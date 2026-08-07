import urllib.request, json, time

data = json.dumps({'domain': 'stripe.com', 'name': 'Stripe'}).encode()
req = urllib.request.Request('http://localhost:8000/analyze', data=data, headers={'Content-Type': 'application/json'}, method='POST')
resp = urllib.request.urlopen(req)
job = json.loads(resp.read().decode())
print('Job created:', json.dumps(job, indent=2))
job_id = job['job_id']

for i in range(15):
    time.sleep(2)
    req2 = urllib.request.urlopen('http://localhost:8000/jobs/' + job_id)
    status = json.loads(req2.read().decode())
    st = status['status']
    cid = status.get('company_id')
    print('Poll ' + str(i+1) + ': status=' + st + ' company_id=' + str(cid))
    if st in ('completed', 'failed'):
        print('Final:', json.dumps(status, indent=2))
        if cid:
            r3 = urllib.request.urlopen('http://localhost:8000/company/' + cid)
            print('Company:', json.dumps(json.loads(r3.read().decode()), indent=2))
            r4 = urllib.request.urlopen('http://localhost:8000/scores/' + cid)
            scores = json.loads(r4.read().decode())
            print('Scores count:', len(scores))
            print('Score types:', [s['score_type'] for s in scores])
        break
