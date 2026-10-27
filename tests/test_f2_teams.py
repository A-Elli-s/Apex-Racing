import importlib.util
import pathlib
import unittest

SCRIPT=pathlib.Path(__file__).resolve().parents[1]/'scripts'/'audit_f2_teams.py'
spec=importlib.util.spec_from_file_location('audit_f2_teams',SCRIPT)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def sample():
    teams={chr(65+i):['D'+str(i*2+1),'D'+str(i*2+2)] for i in range(10)}
    rows=[[str(i),'D'+str(i),str(100-i)] for i in range(1,21)]
    return {'series':'F2','season':2026,'data':{'headers':['Position','Driver','Points'],'rows':rows}}, {'season':2026,'teams':teams}


class F2TeamTests(unittest.TestCase):
    def test_calculation(self):
        d,r=sample();rows=mod.calculate(d,r)
        self.assertEqual(rows[0],['1','A','197'])
        self.assertEqual(len(rows),10)

    def test_published_mismatch_rejected(self):
        d,r=sample();rows=mod.calculate(d,r)
        p={'series':'F2 Teams','data':{'headers':['Position','Team','Points'],'rows':[list(x) for x in rows]}}
        self.assertTrue(mod.audit_published(p,rows))
        p['data']['rows'][0][-1]='999'
        with self.assertRaisesRegex(ValueError,'differ'):
            mod.audit_published(p,rows)

    def test_missing_driver_rejected(self):
        d,r=sample();r['teams']['A'].pop()
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            mod.calculate(d,r)


if __name__=='__main__':
    unittest.main()
