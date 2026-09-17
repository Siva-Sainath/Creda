"""
Strands Agent Loop (Implemented via Bedrock Converse API)

Provides a bounded agent loop (max 4 turns, max 6 tool calls, temperature 0)
that generates a plain-English explanation of the evidence.
"""
import json
import logging
import os
import boto3

logger = logging.getLogger(__name__)

# Re-use the boto3 client from the handler or create a new one
_bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))

def run_strands_agent_loop(
    offer_text: str,
    evidence_records: list,
    employer_profile: dict,
    bedrock_model_id: str,
    guardrail_id: str | None,
    guardrail_version: str | None
) -> dict:
    """
    Runs the bounded agent loop to produce a plain-English explanation
    of the verification results.
    """
    logger.info("Starting Strands Agent loop...")

    # Define tools
    tools = [
        {
            "toolSpec": {
                "name": "get_evidence_records",
                "description": "Get the list of hard evidence records found by the deterministic checks.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {},
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "get_employer_profile",
                "description": "Get the resolved official employer profile and policies.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {},
                    }
                }
            }
        }
    ]

    system_prompts = [{"text": """You are an expert fraud investigator. Your job is to write a plain-English explanation of why a job offer was flagged or verified, based ONLY on the evidence provided by your tools. 
Do not guess. Use the get_evidence_records and get_employer_profile tools to inspect the hard facts. 
Then, output your final explanation in JSON format: {"explanation": "...", "headline": "..."}.
Your explanation should be clear and polite. Do not hallucinate."""}]

    messages = [
        {
            "role": "user",
            "content": [{"text": f"Please analyze this job offer based on the deterministic checks:\n\n{offer_text[:2000]}"}]
        }
    ]

    converse_kwargs = {
        "modelId": bedrock_model_id,
        "system": system_prompts,
        "messages": messages,
        "toolConfig": {"tools": tools},
        "inferenceConfig": {"temperature": 0.0, "maxTokens": 800},
    }

    if guardrail_id and guardrail_version:
        converse_kwargs["guardrailConfig"] = {
            "guardrailIdentifier": guardrail_id,
            "guardrailVersion": guardrail_version,
            "trace": "DISABLED"
        }

    max_turns = 4
    total_tool_calls = 0
    max_tool_calls = 6

    for turn in range(max_turns):
        logger.info(f"Strands Loop Turn {turn + 1}")
        
        try:
            response = _bedrock.converse(**converse_kwargs)
        except Exception as e:
            logger.error(f"Bedrock converse failed: {e}")
            return {"headline": "Could not complete analysis", "explanation": "The AI step did not finish."}
            
        output_message = response['output']['message']
        messages.append(output_message)

        if response['stopReason'] == 'tool_use':
            tool_requests = [c['toolUse'] for c in output_message['content'] if 'toolUse' in c]
            tool_results = []
            
            for tool_req in tool_requests:
                total_tool_calls += 1
                if total_tool_calls > max_tool_calls:
                    logger.warning("Max tool calls exceeded.")
                    break
                    
                tool_name = tool_req['name']
                tool_id = tool_req['toolUseId']
                
                if tool_name == 'get_evidence_records':
                    result_data = json.dumps([e.to_dict() for e in evidence_records], default=str)
                elif tool_name == 'get_employer_profile':
                    result_data = json.dumps(employer_profile, default=str)
                else:
                    result_data = "Unknown tool"

                tool_results.append({
                    "toolResult": {
                        "toolUseId": tool_id,
                        "content": [{"json": {"result": result_data}}]
                    }
                })
                
            messages.append({
                "role": "user",
                "content": tool_results
            })
            
        else:
            # We got a text response. Try to parse JSON.
            text_resp = next((c['text'] for c in output_message['content'] if 'text' in c), "")
            try:
                # Find JSON block if they wrapped it
                start = text_resp.find('{')
                end = text_resp.rfind('}') + 1
                if start != -1 and end != 0:
                    parsed = json.loads(text_resp[start:end])
                    return {
                        "headline": parsed.get("headline", "Investigation Complete"),
                        "explanation": parsed.get("explanation", "The offer has been analyzed based on the evidence.")
                    }
            except json.JSONDecodeError:
                return {"headline": "Investigation Complete", "explanation": text_resp}
                
            break
            
    return {"headline": "Analysis Incomplete", "explanation": "The investigation loop timed out before finishing."}
