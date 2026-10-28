#!/usr/bin/env python3
"""Enrich shortlist traffic using DataForSEO credentials held only in memory."""
import argparse, base64, json, time
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen
from dataforseo_credentials import get_credentials

def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',required=True); p.add_argument('--output',required=True); p.add_argument('--location-code',type=int,default=2840); p.add_argument('--language-code',default='en'); p.add_argument('--chunk-size',type=int,default=50); a=p.parse_args()
    login,password=get_credentials()
    payload=json.loads(Path(a.input).read_text())
    rows=payload.get('shortlist', payload) if isinstance(payload, dict) else payload
    targets=[r.get('normalized_domain') or r.get('domain') for r in rows]
    token=base64.b64encode(f'{login}:{password}'.encode()).decode()
    endpoint='https://api.dataforseo.com/v3/dataforseo_labs/google/bulk_traffic_estimation/live'
    metrics={}; total_cost=0.0
    chunk_size=max(1,min(a.chunk_size,1000))
    for offset in range(0,len(targets),chunk_size):
        chunk=targets[offset:offset+chunk_size]
        body=json.dumps([{'targets':chunk,'location_code':a.location_code,'language_code':a.language_code,'item_types':['organic']}]).encode()
        result=None
        for attempt in range(3):
            try:
                req=Request(endpoint,data=body,headers={'Authorization':f'Basic {token}','Content-Type':'application/json'})
                with urlopen(req,timeout=90) as response: result=json.loads(response.read())
                break
            except Exception:
                if attempt == 2: raise
                time.sleep(2 ** attempt)
        if result.get('status_code')!=20000 or result.get('tasks_error'):
            raise SystemExit(f"DataForSEO error: {result.get('status_code')} {result.get('status_message')}")
        task=result['tasks'][0]; total_cost += float(task.get('cost') or 0)
        items=(task.get('result') or [{}])[0].get('items',[])
        metrics.update({i['target']:i.get('metrics',{}).get('organic',{}) for i in items})
        print(f"[{min(offset+len(chunk),len(targets))}/{len(targets)}] traffic")
    for row in rows:
        organic=metrics.get(row.get('normalized_domain') or row.get('domain'),{}); checks=row.setdefault('quality_checks',{})
        checks.update({'traffic_estimate':organic.get('etv'),'traffic_unit':'estimated monthly organic visits','traffic_source':'DataForSEO Labs Google','traffic_scope':f'location_code={a.location_code}; language={a.language_code}','traffic_checked_at':date.today().isoformat(),'organic_serp_count':organic.get('count')})
    if isinstance(payload, dict):
        payload['dataforseo_cost_usd']=round(total_cost,6)
    else:
        payload={'shortlist': rows, 'dataforseo_cost_usd': round(total_cost,6)}
    Path(a.output).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print(f"Updated {len(rows)} domains; cost ${payload['dataforseo_cost_usd']}")
if __name__=='__main__': main()
