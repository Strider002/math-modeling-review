"""Original dimensionless metric counterexample; no training or upstream code."""
import argparse, hashlib, itertools, json, pathlib
from fractions import Fraction as F

def assess(labels, predictions):
    y=list(map(F,labels)); p=list(map(F,predictions))
    if not y or len(y)!=len(p): raise ValueError('Nonempty equal-length vectors required')
    winners=[i for i,x in enumerate(p) if x==max(p)]
    if len(winners)!=1: raise ValueError('Top prediction must be unique; define a tie policy first')
    i=winners[0]
    return {'mse':sum((a-b)**2 for a,b in zip(y,p))/len(y), 'selected_index':i, 'selected_value':y[i], 'regret':max(y)-y[i]}

def compute():
    y=[F(0),F(1),F(2)]; a=[F(0),F(8,5),F(7,5)]; b=[F(0),F(0),F(29,10)]
    av=assess(y,a);bv=assess(y,b)
    checks={}
    checks['manual_mse']=av['mse']==F(6,25) and bv['mse']==F(181,300)
    checks['smaller_error_worse_selection']=av['mse']<bv['mse'] and av['regret']>bv['regret']
    checks['manual_selection']=av['selected_value']==1 and bv['selected_value']==2
    checks['all_six_joint_permutations']=all(assess([y[i] for i in perm],[a[i] for i in perm])['regret']==1 and assess([y[i] for i in perm],[b[i] for i in perm])['regret']==0 for perm in itertools.permutations(range(3)))
    checks['translation_invariance']=all(assess([v+7 for v in y],[v+7 for v in p])['mse']==assess(y,p)['mse'] and assess([v+7 for v in y],[v+7 for v in p])['regret']==assess(y,p)['regret'] for p in [a,b])
    checks['positive_scaling']=all(assess([3*v for v in y],[3*v for v in p])['mse']==9*assess(y,p)['mse'] and assess([3*v for v in y],[3*v for v in p])['regret']==3*assess(y,p)['regret'] for p in [a,b])
    checks['perfect_predictions']=assess(y,y)['mse']==assess(y,y)['regret']==0
    invalid=0
    for ys,ps in [([],[]),([0],[0,1]),([0,1],[0,0])]:
        try: assess(ys,ps)
        except ValueError: invalid+=1
    checks['invalid_and_tied_inputs_rejected']=invalid==3
    assert all(checks.values()), checks
    def pack(row): return {k:str(v) if isinstance(v,F) else v for k,v in row.items()}
    return {'kind':'original_synthetic_counterexample','units':'dimensionless','labels':list(map(str,y)),'predictions':{'A':list(map(str,a)),'B':list(map(str,b))},'results':{'A':pack(av),'B':pack(bv)},'checks':checks,'upstream_rankreg_executed':False,'script_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');args=ap.parse_args()
    path=pathlib.Path(__file__).with_name('results.json');result=compute()
    if args.check:
        assert json.loads(path.read_text(encoding='utf-8'))==result,'Saved result or script fingerprint differs'
    else:path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('CHECKS=8/8; '+('REPRODUCTION=PASS' if args.check else 'RESULTS_WRITTEN'))
