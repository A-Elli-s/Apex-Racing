import importlib.util
import pathlib
import unittest
from bs4 import BeautifulSoup

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'scripts' / 'update_wikipedia_ladders.py'
spec = importlib.util.spec_from_file_location('update_wikipedia_ladders', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    drivers = ''.join('<tr><th scope="row">' + str(i) + '</th><td>Driver ' + str(i) + '</td><td>1</td><td>' + str(200-i) + '</td></tr>' for i in range(1,13))
    teams = ''.join('<tr><th>' + str(i) + '</th><td>Team ' + str(i) + '</td><td>' + str(200-i) + '</td></tr>' for i in range(1,7))
    html = "<h3>Drivers' Championship standings</h3><table class=\"wikitable\"><tr><th>Pos.</th><th>Driver</th><th>Round</th><th>Points</th></tr>" + drivers + "</table><h3>Teams' Championship standings</h3><table class=\"wikitable\"><tr><th>Pos.</th><th>Team</th><th>Points</th></tr>" + teams + "</table>"
    return BeautifulSoup(html, 'html.parser')


class LadderTests(unittest.TestCase):
    def test_drivers(self):
        result = module.parse_table(fixture(), 'drivers')
        self.assertEqual(len(result['rows']), 12)
        self.assertEqual(result['rows'][0], ['1', 'Driver 1', '199'])

    def test_teams(self):
        result = module.parse_table(fixture(), 'teams')
        self.assertEqual(len(result['rows']), 6)

    def test_rejects_incorrect_point_order(self):
        html = fixture()
        rows = html.select('table')[0].select('tr')
        rows[2].select('td')[-1].string = '999'
        with self.assertRaises(ValueError):
            module.parse_table(html, 'drivers')


if __name__ == '__main__':
    unittest.main()
