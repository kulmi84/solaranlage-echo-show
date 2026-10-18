import json
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from pathlib import Path
import beta_live_reader
import test_beta_live as harness


class HistoryReaderTests(unittest.TestCase):
    def read(self, history, today='2026-10-18'):
        data = {'power_w': 1000, 'received_at': datetime.now(timezone.utc).isoformat(),
                'local_date': today, 'history': history}
        with patch('beta_live_reader.urlopen', return_value=harness.FakeResponse(data)):
            return beta_live_reader.read_pv('https://example.test/pv', 'test')

    def snapshot(self):
        return {'received_at': datetime.now(timezone.utc).isoformat(), 'month_id': '2026-10',
                'year_id': '2026', 'month_pv_kwh': 500, 'year_pv_kwh': 8000,
                'month_grid_export_kwh': 0}

    def test_history_preserves_zero_and_null(self):
        result = self.read(self.snapshot())
        self.assertEqual(result['history']['month_pv_kwh'], 500)
        self.assertEqual(result['history']['month_grid_export_kwh'], 0)
        self.assertIsNone(result['history']['month_home_kwh'])

    def test_new_month_clears_month_but_preserves_same_year(self):
        result = self.read(self.snapshot(), '2026-11-01')
        self.assertIsNone(result['history']['month_pv_kwh'])
        self.assertEqual(result['history']['year_pv_kwh'], 8000)
        result = self.read(self.snapshot(), '2027-01-01')
        self.assertIsNone(result['history']['year_pv_kwh'])

    def test_invalid_history_never_breaks_live_reading(self):
        for change in [{'received_at': 42}, {'month_pv_kwh': -1}, {'year_pv_kwh': True},
                       {'received_at': 'invalid'}, {'month_pv_kwh': float('nan')}]:
            result = self.read({**self.snapshot(), **change})
            self.assertEqual(result['metrics']['power_w'], 1000)
            self.assertEqual(result['history'], {})

    def test_old_history_is_marked_after_six_hours_not_three_minutes(self):
        for hours, stale in [(1, False), (7, True)]:
            data = self.snapshot()
            data['received_at'] = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
            self.assertEqual('VERALTET' in self.read(data)['historyStatus'], stale)


class HistoryDisplayTests(unittest.TestCase):
    event = harness.AutomaticDisplayTests.event
    render = harness.AutomaticDisplayTests.render
    document = harness.AutomaticDisplayTests.document
    def test_two_pages_wrap_right_and_use_independent_thresholds(self):
        response, _ = self.render(1000, self.event())
        doc = self.document(response)
        pager = doc['mainTemplate']['items'][0]['items'][0]
        self.assertEqual(pager['type'], 'Pager')
        self.assertEqual(pager['navigation'], 'wrap')
        self.assertEqual(len(pager['items']), 2)
        self.assertIn('utcTime >= 1060000', doc['mainTemplate']['items'][0]['handleTick'][0]['when'])
        self.assertIn('utcTime >= 22600000', doc['mainTemplate']['items'][0]['handleTick'][0]['when'])
        self.assertIn('currentPage == 1', doc['mainTemplate']['items'][0]['handleTick'][0]['when'])

    def test_refresh_preserves_selected_page_and_original_deadline(self):
        response, _ = self.render(1060, self.event(['auto_refresh', 4600000, 1]))
        doc = self.document(response)
        self.assertEqual(doc['mainTemplate']['items'][0]['items'][0]['initialPage'], 1)
        self.assertEqual(doc['settings']['idleTimeout'], 3540000)

    def test_invalid_page_is_not_accepted(self):
        for page in [True, 2, -1, '1']:
            response, reader = self.render(1060, self.event(['auto_refresh', 4600000, page]))
            reader.assert_not_called()
            self.assertEqual(response['response'], {})


class HistoryHaTemplateTests(unittest.TestCase):
    def test_template_sums_month_year_separately_in_kwh(self):
        import yaml
        from jinja2 import Environment
        class Loader(yaml.SafeLoader): pass
        Loader.add_constructor('!secret', lambda loader, node: loader.construct_scalar(node))
        package = yaml.load(Path('home-assistant/pv_history.yaml').read_text(encoding='utf-8'), Loader=Loader)
        automation = package['automation'][0]
        self.assertEqual(automation['triggers'][0]['hours'], '/6')
        self.assertEqual(automation['actions'][1]['data']['period'], 'month')
        self.assertEqual(automation['actions'][2]['data']['period'], 'year')
        env = Environment()
        env.filters['from_json'] = json.loads
        env.globals['as_datetime'] = datetime.fromisoformat
        ids = automation['actions'][1]['data']['statistic_ids']
        month = {'statistics': {key: [{'change': 10}] for key in ids}}
        year = {'statistics': {key: [{'change': 100}] for key in ids}}
        source = automation['actions'][-1]['data']['solar_data']
        output = env.from_string(source).render(month_stats=month, year_stats=year,
                                               history_now='2026-10-18T12:00:00+02:00')
        import ast
        data = ast.literal_eval(output.strip())
        self.assertEqual(data['month_pv_kwh'], 20)
        self.assertEqual(data['year_pv_kwh'], 200)
        self.assertEqual(data['month_home_kwh'], 20)
        self.assertEqual(data['month_id'], '2026-10')
        output = env.from_string(source).render(month_stats={}, year_stats={},
                                               history_now='2026-10-18T12:00:00+02:00')
        self.assertIsNone(ast.literal_eval(output.strip())['month_pv_kwh'])


if __name__ == '__main__': unittest.main()
