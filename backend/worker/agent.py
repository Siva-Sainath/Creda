"""
Strands Agent Loop (Implemented via the Strands Agents SDK)
"""
import json
import logging
from strands import Agent, tool

logger = logging.getLogger(__name__)

def run_strands_agent_loop(
    offer_text: str,
    evidence_records: list,
    employer_profile: dict,
    bedrock_model_id: str,
    guardrail_id: str | None,
    guardrail_version: str | None
) -> dict:
    """
    Runs the bounded agent loop using the Strands SDK to produce a plain-English explanation
    of the verification results.
    """
    logger.info("Starting true Strands Agent loop...")

    @tool
    def get_evidence_records() -> str:
        """Get the list of hard evidence records found by the deterministic checks."""
        return json.dumps([e.to_dict() for e in evidence_records], default=str)

    @tool
    def get_employer_profile() -> str:
        """Get the resolved official employer profile and policies."""
        return json.dumps(employer_profile, default=str)

    system_prompt = """You are an expert fraud investigator. Your job is to write a plain-English explanation of why a job offer was flagged or verified, based ONLY on the evidence provided by your tools. 
Do not guess. Use the get_evidence_records and get_employer_profile tools to inspect the hard facts. 
Then, output your final explanation in JSON format: {"explanation": "...", "headline": "..."}.
Your explanation should be clear and polite. Do not hallucinate."""

    # Initialize the Strands SDK Agent
    # Bedrock is the default provider for Strands.
    agent = Agent(
        tools=[get_evidence_records, get_employer_profile],
        model=bedrock_model_id,
        system_prompt=system_prompt,
        max_steps=4  # Bound the loop to prevent runaway costs
    )

    try:
        user_prompt = f"Please analyze this job offer based on the deterministic checks:\n\n{offer_text[:2000]}"
        response = agent(user_prompt)
        
        # We got a text response. Try to parse JSON.
        text_resp = response if isinstance(response, str) else str(response)
        
        start = text_resp.find('{')
        end = text_resp.rfind('}') + 1
        if start != -1 and end != 0:
            parsed = json.loads(text_resp[start:end])
            return {
                "headline": parsed.get("headline", "Investigation Complete"),
                "explanation": parsed.get("explanation", "The offer has been analyzed based on the evidence.")
            }
        return {"headline": "Investigation Complete", "explanation": text_resp}
        
    except json.JSONDecodeError:
        return {"headline": "Investigation Complete", "explanation": text_resp}
    except Exception as e:
        logger.error(f"Strands agent failed: {e}")
        return {"headline": "Analysis Incomplete", "explanation": "The AI investigation loop encountered an error."}
