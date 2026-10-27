import importlib.util
import pathlib
import unittest

SCRIPT=pathlib.Path(__file__).resolve().parents[1]/'scripts'/'calculate_f3_teams.py'
spec=importlib.util.spec_from_file_location('calculate_f3_teams',SCRIPT)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def sample():
    teams={'A':['D1','D2','D3'],'B':['D4','D5','D6'],'C':['D7','D8','D9'],'D':['D10','D11','D12'],'E':['D13','D14','D15'],'F':['D16','D17','D18'],'G':['D19','D20','D21'],'H':['D22','D23','D24']}
    rows=[[str(i),'D'+str(i),str(100-i)] for i in range(1,25)]
    expected={team:sum(100-int(n[1:]) for n in names) for team,names in teams.items()}
    return {'series':'F3','season':2026,'data':{'headers':['Position','Driver','Points'],'rows':rows}}, {'season':2026,'teams':teams,'verified_totals':expected}


class F3TeamsTests(unittest.TestCase):
    def test_calculates_and_verifies(self):
        d,r=sample();out=mod.calculate(d,r)
        self.assertEqual(len(out['rows']),8)
        self.assertEqual(out['rows'][0],['1','A','294'])

    def test_rejects_unmapped_driver(self):
        d,r=sample();r['teams']['A'].remove('D1')
        with self.assertRaisesRegex(ValueError,'does not cover'):
            mod.calculate(d,r)

    def test_rejects_mismatched_independent_total(self):
        d,r=sample();r['verified_totals']['A']=999
        with self.assertRaisesRegex(ValueError,'differ'):
            mod.calculate(d,r)


if __name__=='__main__':
    unittest.main()
