# AWS ingestion manifest (documentation only — no resources deployed)

Generated: 2026-09-17
Processing version: creda-preprocess-2.0

## S3 prefix layout

```
s3://creda-data/
  raw/{source_id}/{retrieval_date}/          # immutable bytes + sidecar metadata
  curated/evidence/{evidence_id}.json          # canonical records
  curated/evidence.parquet                       # Glue/Bedrock-friendly table
  curated/patterns.jsonl
  curated/employer_policies.jsonl
  curated/evaluation_cases.jsonl
  curated/source_snapshots/{retrieval_date}/
  quarantine/{source_id}/
  private/gmail/                                 # never public ACL
  manifests/{retrieval_date}/ingestion.json
  bedrock/documents/{evidence_id}.json       # metadata adjacent to source refs
```

## Record manifest

| source_id | records | sample_checksum | permissions |
|---|---:|---|---|
| `accenture_recruitment_fraud_policy` | 1 | `e37128e06fa3a06517b29b9b708888fbc4fcd253e3eca87bef37b7544695fade` | public |
| `amazon_jobs` | 1 | `f98835ce24db408702534151cdcb91ef099d712dd636e0dc088f25da462bb762` | public |
| `amazon_recruitment_fraud_policy` | 1 | `5d2e64eaa49318bd87ee57112518d58cc585900b7d6f2ca8fee10dbe52f3d216` | public |
| `amex_recruitment_fraud_policy` | 1 | `cbfbee994f6afd6f6014e3a7a2b17133dc1f4090f08d7cbbf3844827a60df770` | public |
| `ashby_notion_jobs` | 128 | `73c5c582184f7ea1144a96ed4ea498d0221892c1ae50995a8c7b5d0fb31d593f` | public |
| `ca_ag_job_scam_alert_2025` | 1 | `25be4814129cd657d83c4a6f0c6372995006f4e6f97e2db59d00fa0a875bb595` | public |
| `capgemini_recruitment_fraud_policy` | 1 | `2fb5d70a21308637015bc47ede0716a25f89f7d3f26a264b38b4d4546ecbd888` | public |
| `cognizant_recruitment_fraud_policy` | 1 | `a275c4b31c0eea056213519ec981a9ba3d6370710f2f805c45623f07b63e8453` | public |
| `cyberdost_job_fraud_tips` | 1 | `d1c279a0a39c2acc9fa49cf2339e69fdf7683efa4e496796896bce9a7af596ee` | public |
| `difraud_job_scams` | 14295 | `ed64c355d9a571e675804e0d83b9b27d29b475fd4b6b9c96f20a0874db3b322c` | public |
| `emigrate_portal` | 1 | `11b0d8225e72d68252ff3477b298757f6eeebf261b23bcc8e880f349cff69819` | public |
| `emscad` | 17880 | `1ff86fee5f473f181c0721af34ce64b6591da88c4a804d628ae772ba1011d0dc` | public |
| `flipkart_recruitment_fraud_policy` | 1 | `3bbafa1299689f870aa0d9c070caa3e24d55a6d4351ee80b9eca193769686bdc` | public |
| `freshworks_recruitment_fraud_policy` | 1 | `05960ae5d0aea047373126634a8b5184bdfacb8cbb22c7f5b378db8d51d29fe8` | public |
| `ftc_job_scams` | 1 | `5305f3585370392e7db08d782da7c258483fb7eb7aed1aaac885e470d58c5e9e` | public |
| `gmail_inbox_search` | 14 | `n/a` | private |
| `google_recruitment_fraud_policy` | 1 | `48a085e6b0332564192482ddd64dceaa09e0ddc02ce229139886a5855cf0ec3a` | public |
| `greenhouse_airbnb_jobs` | 163 | `b7a7f3c705fff87ce327f303c437cd7fb713c168e218380b98f359f48dcd875e` | public |
| `greenhouse_anthropic_jobs` | 607 | `834f34c45d01cd8664c24161eb76453e7c899cca666a273ce7ca0e0740d0bd1a` | public |
| `greenhouse_cloudflare_jobs` | 361 | `b6db2d96f0ab306dc94f76295be3a787061842b0fb63ad267c1425871318df49` | public |
| `greenhouse_coinbase_jobs` | 220 | `1f81a8c3fbdfcbf8b4de8de86aae69635b972d64c5a270756676114e3348a257` | public |
| `greenhouse_databricks_jobs` | 879 | `f9ac681c150d28f0370509ed522b4da9a59b75c85fd6a8ea53a7f0fff5e4485a` | public |
| `greenhouse_datadog_jobs` | 451 | `1f87e0dd8f59b939371d2e20c8b7f3877f8af7dace68738f6412236057304c1a` | public |
| `greenhouse_discord_jobs` | 47 | `3e6e361f82d7de2d0bcbd55f59c31dba1242f250bed79bd2dc0bb77a01260027` | public |
| `greenhouse_figma_jobs` | 154 | `a5b6dbd896a980009396d77c6a1748bd5742870dcd09786b1718c84ed46fca5c` | public |
| `greenhouse_instacart_jobs` | 108 | `91ee2a7fb5b8fb6aa1eddcd060486a74b69f724e582a4f723a2c6db0ae1aaeaa` | public |
| `greenhouse_job_board_api` | 1 | `666dca356fa154a91e382fe55c007d004c67abb79fb6f7f97055e2d1668c5794` | public |
| `greenhouse_lyft_jobs` | 183 | `bf1ce614961069e77028810e6cdd2bba6b4a3a05f8947fc6dd41a1fddf384b33` | public |
| `greenhouse_mongodb_jobs` | 411 | `0facc109771ff733ca7d90999fa9b258b70d197057c3b0c5f837919fa85a88c1` | public |
| `greenhouse_reddit_jobs` | 154 | `09d15d29a5674546c71545dc2ba157b3299136665660c982fa356085ce184608` | public |
| `greenhouse_stripe_jobs` | 652 | `83587d3171b9cf48f911232fc70830ff407c2122f1cc14e3f59e5f68c5a9d109` | public |
| `greenhouse_twilio_jobs` | 148 | `75e8aea2c37517d7d1687696a64761dfb799327841cd399710e4fd16f4754d7f` | public |
| `greenhouse_vercel_jobs` | 87 | `6c106caa3fd4a1de453c40ac170e419726d13fc4bbb88cb2372c3053ff877b21` | public |
| `hcl_recruitment_fraud_policy` | 1 | `f9ba57e3a5b27f65e8aa20c8f29428570c1fbc81052772b26a1bd1d5ffdd40e8` | public |
| `i4c_captcha_advisory_2025` | 1 | `ddc3af554e0bf09cdf361a55f4b530cd0dcb820703198175851d8e31947f589d` | public |
| `i4c_cybercrime_portal` | 1 | `629fc2265824c6d641e1540fb3f316a8088b3a71ae783cca1c6ced8a2295ad19` | public |
| `i4c_fake_job_sms_advisory` | 1 | `c09c42351be2a82a4c84561003093c316ebc3eb78a4c872ce57ee90eb7c550a5` | public |
| `i4c_handbook_2025` | 1 | `16028474ce956b43760956c0d49d20fe018be7960d8cc23dc0a9cc02ab3af95f` | public |
| `ibm_recruitment_fraud_policy` | 1 | `cff7e8e78174f056c603b8f523b5981d00162f02e2f14c3859d977b4ea505bbc` | public |
| `ic3_annual_report_2024` | 1 | `ba494b0a1bd991c722cf65619eb518329175b898fb508e8c84fc7dd12e07cac0` | public |
| `infosys_recruitment_fraud_policy` | 1 | `81277eae1a33b90d494354c9fc17f88afe78e836bd8abd2fc0c8d55e5e675893` | public |
| `kaggle_fake_vs_real_synthetic` | 3000 | `a00014bd642b9e89d95b52708271b8e6396a5b54657c6fe0f529eb648799d9e7` | public |
| `kpmg_recruitment_fraud_policy` | 1 | `0a42e5848adac582e5189cd60aa87295ef2d38eee9d9312d4ba701ac15390f8a` | public |
| `lever_postings_api` | 1 | `6f94b9d9a5d4efe8d44c770e0a2559cc4ad78897f12e268cbfa2a84344deba08` | public |
| `lever_spotify_jobs` | 69 | `7c58c6fde8f8dc06a77eefd94906881b7a641115240d952d7baf47123ff74bbc` | public |
| `linkedin_job_scam_guidance` | 1 | `0e19872d7f5b6ec1a90438460c7e13f6974ba8a78e41bbb81b657711bf2178b5` | public |
| `mea_overseas_employment` | 1 | `dbf08583c8a263e00c533ee177ae89ca0c51c6dd53fea4214d867b763cc51772` | public |
| `mea_yangon_overseas_job_scam_2024` | 1 | `ad164e9485a1a82d5f6c24692fd2d49f6b243183f99e6e875c8ce7e80fe80fcc` | public |
| `microsoft_recruitment_fraud_alert` | 1 | `2988e80093cc650bce64f868e364144cfb0bcca79481b2cbb8ded9212d152fbe` | public |
| `nasc_job_scam_fusion_report_2025` | 1 | `c48ea5689298432f837d8553f3464c1aacabdab7855ffb828e9786844411e581` | public |
| `ncsc_phishing_guidance` | 1 | `b1fc479da41b2b40480c496823977f0f56f1975227b5e56d3fc546d8ee938bfe` | public |
| `netapp_recruitment_fraud_policy` | 1 | `914b42ba5c87b37ddb2ec61e3a0c24b608b6954662412f1aa51602f333a908ef` | public |
| `oracle_recruitment_fraud_policy` | 1 | `9aa8ce8e38ed8eb3dd28e433148ab69f8041f15da2b25ffbff8a4b684ada7fb7` | public |
| `razorpay_recruitment_fraud_policy` | 1 | `de45aa2c206cd9475d3ea162999bdc1d6de652dfb882a5cd1e2cc3c6d93da458` | public |
| `scamwatch_au_job_scams` | 1 | `0616693a1f0871f294e8526658453ecbf9a3980192cfaac64868b7481b87ca10` | public |
| `smartrecruiters_api_docs` | 1 | `faa99bcca8ab590b9e974a4fac5bc80d34fd234bfd9f45bbfb3a46f274c036df` | public |
| `tcs_recruitment_fraud_policy` | 1 | `322791d8f8291a4a7bb2eaf5ab3bfbb3c44b9e991aa0ce8fc94cadcf2c8dabc3` | public |
| `tech_mahindra_recruitment_fraud_policy` | 1 | `eac0ab1905f7226a5023d172fff8ecc0b403d59c20551b89ca129a1b283313ab` | public |
| `valero_recruitment_scams_2025` | 1 | `a021c0c50e0431db343dd5af092c74314adc46235ef32669824c19d00cd9ac3f` | public |
| `wipro_recruitment_fraud_policy` | 1 | `4ebca0f739af0d8343d0852b00d0650ad93dbf20e0ab2d4c99f99dba20cdf045` | public |
| `yc_jobs` | 1 | `f69850276ccd15f0704f9a4800dea09306f59a828a4060f56ad96cb3da80756a` | public |
| `zoho_recruitment_fraud_policy` | 1 | `c87755a5401c25bbba5bd5f78b288fe3f0329bc94e95bbd8041f29015aa9c33b` | public |

## Parquet

- Path: `data/curated/evidence.parquet`
- Rows: 40052
- Columns: 56

## Glue

Use `schemas/glue_evidence_table.json` (generated) with partition key `source_id`.

## Bedrock Knowledge Base

Store document bodies in S3; keep metadata JSON adjacent. Do **not** store full bodies in DynamoDB.

## Estimated monthly cost (if deployed — requires approval)

| Service | Assumption | Est. USD/month |
|---|---|---|
| S3 Standard | ~500 MB curated + 120 MB raw | $0.02 |
| Glue Crawler | weekly on curated prefix | $1-3 |
| Athena | 10 GB scanned / month | $0.05 |
| Bedrock KB sync | 50k docs, monthly refresh | $5-15 |
| **Total** | dev/staging footprint | **~$6-20** |

No AWS resources are created by this pipeline run.
