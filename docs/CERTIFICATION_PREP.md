# E-Parking v2 — Certification Preparation Guide

> **Date:** 26 April 2026
> **Purpose:** Guide for achieving BI certification and acquirer approval for production e-money processing

---

## 1. Bank Indonesia (BI) Certification

### Overview
BI certification is **mandatory** for any payment system processing Indonesian e-money (Mandiri eMoney, BRI Brizzi, BNI TapCash, BCA Flazz, etc.).

### Certification Process

```
Phase 1: Documentation (2-3 weeks)
├── Business license (SIUP/TDP/NIB)
├── NPWP
├── Domicile letter
├── Merchant agreement with acquirer
├── System security documentation
└── Technical architecture review

Phase 2: Technical Testing (2-4 weeks)
├── Security penetration testing
├── Compliance testing (BI regulation 19/12/PBI/2017)
├── Transaction flow validation
├── Settlement file validation
└── Disaster recovery testing

Phase 3: Approval (1-2 weeks)
├── BI review of test results
├── Site inspection (if required)
└── Production approval letter
```

### Required Documents

| Document | Source | Status |
|----------|--------|--------|
| NPWP (Tax ID) | DJP | ⬜ Obtain |
| NIB (Business ID) | OSS | ⬜ Obtain |
| SIUP/TDP | Local government | ⬜ Obtain |
| Domicile letter | Kelurahan | ⬜ Obtain |
| Business bank account | Bank | ⬜ Open |
| Merchant application | Acquirer | ⬜ Submit |
| System security audit | Third party | ⬜ Schedule |

### BI Regulations Reference

- **PBI 19/12/PBI/2017**: Payment transaction processing
- **SEBI 22/15/DPNP**: E-money technical standards
- **PBI 20/6/PBI/2018**: Payment service provider licensing

---

## 2. PCI DSS Compliance

### Scope Assessment

The E-Parking system **does NOT store full card PANs** or sensitive authentication data. It processes:
- Card number (not PAN — this is the e-money card identifier)
- Balance amounts
- Transaction counters
- Encrypted card logs (from PASSTI reader)

### PCI DSS Requirements That Apply

| Requirement | Applicability | Implementation |
|-------------|---------------|----------------|
| 1: Firewall | ✅ | Controller networks isolated via VLAN |
| 2: Default passwords | ✅ | No default passwords in system |
| 3: Stored data protection | ⚠️ | Card numbers stored; ensure DB encryption at rest |
| 4: Encryption in transit | ✅ | HTTPS/TLS 1.3 in nginx |
| 5: Anti-virus | ⚠️ | Linux systems; maintain OS patches |
| 6: Secure development | ✅ | Input validation, parameterized queries |
| 7: Need-to-know access | ✅ | Role-based access control |
| 8: Authentication | ✅ | JWT + password hashing |
| 9: Physical access | ⚠️ | Secure server room / data center |
| 10: Logging | ✅ | Audit logs + structured logging |
| 11: Security testing | ⚠️ | Annual penetration test required |
| 12: Security policy | ⚠️ | Document and maintain |

### Recommendations

1. **Encrypt database at rest** — Use PostgreSQL TDE or filesystem encryption
2. **Encrypt card numbers** — Consider encrypting `ParkingTransaction.card_number` column
3. **Annual penetration test** — Schedule with certified third party
4. **Security policy document** — Create and maintain

---

## 3. SAM Module Requirements

### What is SAM?

**Secure Access Module (SAM)** is a hardware security chip inside the PASSTI reader that:
- Authenticates real e-money cards
- Validates card signatures
- Prevents counterfeit card acceptance

### Dev Kit vs Production Reader

| Feature | Dev Kit | Production Reader |
|---------|---------|-------------------|
| SAM module | ❌ No | ✅ Yes |
| Real card processing | ❌ Test cards only | ✅ All e-money cards |
| BI certification | ❌ Not certified | ✅ Certified |
| Price | Lower | Higher |

### Procurement Checklist

- [ ] Contact PT Softorb for production reader quote
- [ ] Specify SAM module requirement
- [ ] Request BI certification documents from Softorb
- [ ] Order spare readers (N+1 redundancy)
- [ ] Plan serial port assignments per gate

### SAM-Related Code Changes

**No code changes required.** The same PASSTI protocol commands work with both dev kit and production readers. The only difference is:
- Dev kit: INIT key is generic/test key
- Production: INIT key is unique per reader, provided by acquirer

---

## 4. Settlement Compliance

### File Format Compliance

The settlement file generator (`workers/background/settlement_file.py`) produces files compliant with:
- **Format File Settlement Multibank v1.3**
- **BI SEBI 22/15/DPNP** settlement requirements

### Validation Checklist

- [ ] Filename format: `YYYYMMDDHHMMSS + MID(16) + TID(8) + Version(2) + BatchNo(3) + .txt`
- [ ] Header: `count(3) + amount(10)`
- [ ] Body: Raw transaction log data
- [ ] File must be uploaded daily
- [ ] Response file (.OK/.NOK) must be processed

### Test Scenarios

1. Generate settlement with 0 transactions → empty file? (check acquirer spec)
2. Generate settlement with 999 transactions → boundary test
3. Generate with mixed card types → all supported
4. Verify SHA256 hash matches file content

---

## 5. Acquirer Integration

### Supported Acquirers

| Acquirer | Contact | Requirements |
|----------|---------|--------------|
| Luminos | www.luminos.co.id | Merchant agreement, SIUP, NPWP |
| Artajasa | www.artajasa.co.id | Merchant registration, terminal specs |
| Jalin | www.jalin.co.id | BUMN process, longer timeline |
| Rintis | www.rintis.com | BCA-affiliated, BCA account required |

### Merchant Setup Steps

1. **Choose acquirer** based on fee structure and timeline
2. **Submit merchant application** with all business documents
3. **Sign acquirer agreement** (typically 2-3 year term)
4. **Receive MID/TID** — 16-digit MID, 8-digit TID
5. **Receive production init keys** — one per reader
6. **Configure SFTP/API** for settlement upload
7. **Test settlement upload** in sandbox environment
8. **Go live** after BI approval

---

## 6. Pre-Certification Test Plan

### Internal Testing (Before BI Submission)

| Test | Owner | Timeline |
|------|-------|----------|
| Functional testing | QA | 1 week |
| Security testing | Security team | 1 week |
| Performance testing | DevOps | 3 days |
| Settlement validation | Finance | 2 days |
| Disaster recovery drill | Ops | 1 day |
| Penetration test | Third party | 1-2 weeks |

### Required Test Evidence

- Test reports with signatures
- Screenshots of all payment flows
- Settlement file samples
- API response logs
- Security scan results
- Backup/restore verification

---

## 7. Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Business documents | 2-4 weeks | Legal entity exists |
| Acquirer application | 2-4 weeks | Business documents |
| Hardware procurement | 2-3 weeks | Acquirer approval |
| System deployment | 1-2 weeks | Hardware arrival |
| Internal testing | 2-3 weeks | Deployment complete |
| Penetration test | 1-2 weeks | Internal testing pass |
| BI submission | 1 week | All docs ready |
| BI review | 2-4 weeks | BI workload |
| **Total** | **12-24 weeks** | **Parallel where possible** |

---

## 8. Contacts

| Organization | Contact | What to Ask |
|-------------|---------|-------------|
| PT Softorb | +62 21 29668601 | "Saya mau upgrade ke reader produksi dengan SAM module untuk parking system" |
| Luminos | www.luminos.co.id | "Saya ingin menjadi merchant untuk sistem parking dengan e-money" |
| BI | www.bi.go.id | "Proses sertifikasi sistem pembayaran parking" |

---

*This document should be updated as the certification process progresses.*
