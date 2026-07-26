import urllib.request
import json

BASE = 'http://127.0.0.1:8000'
HEADERS = {'X-Employee-ID': 'RM-999', 'X-Session-ID': 'SESS-MP', 'Content-Type': 'application/json'}

def post(path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode('utf-8'), headers=HEADERS)
    res = urllib.request.urlopen(req)
    return json.loads(res.read().decode('utf-8'))

# 1. Create case
created = post('/api/v2/sales-cases', {
    'company_name': 'Công ty Cổ phần Thiết bị Minh Phát',
    'tax_code': '0109988665',
    'industry': 'Phân phối thiết bị công nghiệp',
    'need_text': 'Doanh nghiệp muốn chi lương cho 500 nhân viên và quản lý dòng tiền.',
    'rm_note': 'Live UI Test',
    'priority': 'normal',
    'current_products': []
})
case_id = created['case_id']
print('1. Case Created:', case_id)

# 2. Upload Document
with open('data/mau_ho_so_doanh_nghiep_MINH_PHAT.txt', 'rb') as f:
    doc_content = f.read()

boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
body = (
    b'--' + boundary.encode('utf-8') + b'\r\n'
    b'Content-Disposition: form-data; name="files"; filename="mau_ho_so_doanh_nghiep_MINH_PHAT.txt"\r\n'
    b'Content-Type: text/plain\r\n\r\n' +
    doc_content +
    b'\r\n--' + boundary.encode('utf-8') + b'--\r\n'
)

req = urllib.request.Request(BASE + f'/api/v2/sales-cases/{case_id}/documents', data=body, headers={
    'X-Employee-ID': 'RM-999', 'X-Session-ID': 'SESS-MP',
    'Content-Type': 'multipart/form-data; boundary=' + boundary
})
res = urllib.request.urlopen(req)
print('2. Document Uploaded:', res.status)

# 3. Process Documents
processed = post(f'/api/v2/sales-cases/{case_id}/process-documents', {})
print('3. Processed Status:', processed.get('intake_status'))
version = processed['version']

# Resolve any conflicts if needed
conflicts = processed.get('conflicts', [])
if conflicts:
    changes = []
    for c in conflicts:
        if c.get('requires_confirmation'):
            changes.append({'field_name': c['field_name'], 'value': c['candidates'][0]['value'], 'reason': 'RM confirm'})
    if changes:
        req_patch = urllib.request.Request(BASE + f'/api/v2/sales-cases/{case_id}/extracted-profile', data=json.dumps({
            'expected_version': version, 'changes': changes
        }).encode('utf-8'), headers=HEADERS, method='PATCH')
        res_patch = json.loads(urllib.request.urlopen(req_patch).read().decode('utf-8'))
        version = res_patch['version']

# 4. Confirm Profile
confirmed = post(f'/api/v2/sales-cases/{case_id}/confirm-profile', {'expected_version': version, 'attestation': True})
print('4. Profile Confirmed, version:', confirmed.get('version'))

# 5. Run Analysis
analysis = post(f'/api/v2/sales-cases/{case_id}/run-analysis', {'expected_version': confirmed['version']})
case_data = analysis['case']
print('\n==================================================')
print('5. CASE STATUS AFTER ANALYSIS:', case_data['status'])
print('==================================================')

elig = case_data.get('eligibility_result', {})
print('\nEligibility Products Status:')
for p in elig.get('products', []):
    print(' Product:', p['product_id'], 'Status:', p['status'])
    for r in p.get('rules', []):
        print('   - Rule:', r['rule_id'], 'Status:', r['status'], 'Title:', r.get('title'))

gaps = case_data.get('operations_result', {}).get('required_document_checklist', [])
print('\nDocument Checklist Gaps:')
for g in gaps:
    print(' - Document:', g['display_name'], 'Status:', g['current_status'])

print('\nRisk Gate Result:', json.dumps(case_data.get('risk_gate_result'), indent=2, ensure_ascii=False))
