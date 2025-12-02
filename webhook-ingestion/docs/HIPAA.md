# HIPAA Compliance Considerations

## Overview

The Axentra Webhook Ingestion System is designed with HIPAA compliance in mind. This document outlines the compliance measures implemented and considerations for handling Protected Health Information (PHI).

## Key HIPAA Requirements

### 1. Administrative Safeguards

**Access Controls:**
- IAM roles with least privilege principle
- Separate execution roles for Lambda functions
- No shared credentials
- Regular access reviews recommended

**Audit Controls:**
- Comprehensive CloudWatch logging
- S3 access logging enabled
- DynamoDB audit trail
- Immutable event registry

**Workforce Training:**
- All team members handling PHI must complete HIPAA training
- Regular security awareness updates

### 2. Physical Safeguards

**AWS Infrastructure:**
- AWS data centers are HIPAA-eligible
- Physical security managed by AWS
- No physical access required by team

### 3. Technical Safeguards

#### Encryption

**At Rest:**
- S3: Server-side encryption (SSE-S3) with AES-256
- DynamoDB: Encryption at rest enabled by default
- All stored payloads encrypted

**In Transit:**
- HTTPS/TLS for all webhook communications
- EventBridge API destination uses HTTPS
- Lambda to S3/DynamoDB uses encrypted connections

#### Access Control

**Authentication:**
- EventBridge connection requires API key authentication
- Lambda execution via IAM roles only
- No hardcoded credentials

**Authorization:**
- IAM policies restrict access to minimum required permissions
- S3 bucket policies prevent public access
- DynamoDB access via IAM roles only

#### Audit Controls

**Logging:**
- All Lambda invocations logged to CloudWatch
- S3 access logging enabled
- Event registry in DynamoDB provides audit trail
- Raw payloads stored immutably in S3

**Retention:**
- 7-year retention for audit trail (HIPAA requirement)
- S3 lifecycle policies enforce retention
- DynamoDB TTL for automatic cleanup after retention period

## PHI Handling Considerations

### Fields Containing PHI

Based on the payload schema, the following fields may contain PHI:

**Potentially PHI:**
- `user_id` - May identify patients
- Any fields containing patient names, addresses, or identifiers
- Medical record numbers or identifiers

**Note:** The current payload schema from Axentra appears to be product/catalog data, which may not contain PHI. However, this should be verified with Axentra.

### Field Stripping and PHI

**Fields Removed (Not PHI):**
- `created_at`, `updated_at`, `archived_at` - Timestamps
- `image_url` - Product images
- `stock_quantity`, `is_default`, `stockStatus` - Inventory data
- `lab_test_codes_id`, `service_product_id`, `cpr_price` - Product metadata

**Important:** The field stripping logic does NOT currently remove PHI. If the payload contains PHI, additional fields must be stripped or redacted.

### Recommendations

1. **Verify Payload Contents:**
   - Confirm with Axentra that webhook payloads do not contain PHI
   - If PHI is present, implement additional field stripping

2. **PII Guardrails:**
   - Implement PII detection in Lambda function
   - Add validation to reject payloads containing unexpected PHI
   - Log any PHI detection for audit purposes

3. **Interface Considerations:**
   - Ensure any admin interfaces do not display PHI
   - Implement access controls on monitoring dashboards
   - Restrict CloudWatch log access to authorized personnel only

4. **Vector Store and Summarization:**
   - Confirm that vector stores exclude PII/PHI
   - Ensure summarization modules do not include PHI
   - Implement PII redaction before vectorization

## Compliance Checklist

### Before Production Deployment

- [ ] Verify payload schema does not contain PHI
- [ ] Confirm all encryption is enabled
- [ ] Review IAM policies for least privilege
- [ ] Enable S3 access logging
- [ ] Configure CloudWatch log retention (7 years)
- [ ] Set up monitoring and alerting
- [ ] Document data flow and access controls
- [ ] Complete Business Associate Agreement (BAA) with AWS
- [ ] Verify Axentra has signed BAA if they are a Business Associate
- [ ] Implement PII detection and redaction if needed
- [ ] Review and approve field stripping logic
- [ ] Test idempotency and error handling
- [ ] Document incident response procedures

### Ongoing Compliance

- [ ] Regular access reviews (quarterly recommended)
- [ ] Monitor for unauthorized access attempts
- [ ] Review CloudWatch logs for anomalies
- [ ] Update security patches regularly
- [ ] Conduct periodic security audits
- [ ] Review and update IAM policies as needed
- [ ] Verify retention policies are working correctly

## Data Minimization

The system implements data minimization through:

1. **Field Stripping:** Removes unnecessary fields before processing
2. **Selective Storage:** Only stores required data in processed format
3. **Raw Payload Storage:** Complete payload stored for audit, but with encryption and access controls

## Breach Notification

In the event of a potential breach:

1. **Immediate Actions:**
   - Isolate affected systems
   - Preserve logs and evidence
   - Notify security team

2. **HIPAA Requirements:**
   - Notify affected individuals within 60 days
   - Notify HHS within 60 days (if 500+ individuals affected)
   - Notify media if 500+ individuals in one state affected

3. **Documentation:**
   - Document breach details
   - Maintain incident log
   - Update security procedures

## Business Associate Agreements (BAA)

### AWS BAA

AWS offers a HIPAA BAA. Ensure:
- BAA is signed and active
- Only HIPAA-eligible services are used
- Services used are covered under the BAA

### Axentra BAA

If Axentra is a Business Associate:
- Ensure BAA is in place
- Verify they have appropriate safeguards
- Document data sharing agreements

## Recommendations for Next Steps

1. **Immediate:**
   - Verify payload schema with Axentra (confirm no PHI)
   - Review field stripping requirements
   - Confirm vector store and summarization exclude PII

2. **Before Production:**
   - Implement PII detection if needed
   - Complete security review
   - Sign necessary BAAs
   - Set up monitoring and alerting

3. **Ongoing:**
   - Regular compliance reviews
   - Security updates and patches
   - Access control reviews
   - Audit log reviews

## Resources

- [AWS HIPAA Compliance](https://aws.amazon.com/compliance/hipaa-compliance/)
- [HHS HIPAA Guidance](https://www.hhs.gov/hipaa/index.html)
- [HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html)

## Questions to Address

Before finalizing the system, confirm with Axentra:

1. Does the webhook payload contain any PHI?
2. What fields, if any, contain patient identifiers?
3. Are there any additional fields that should be stripped for HIPAA compliance?
4. What is the data retention requirement from their side?
5. Do they have a BAA in place?




