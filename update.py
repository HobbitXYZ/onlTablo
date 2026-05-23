#!/usr/bin/env python3
"""
Fetches fresh results from sportvokrug.ru GraphQL API and regenerates index.html
Run: python3 update.py [event_id] [out_dir]
"""
import json, datetime, urllib.request, urllib.error, os, sys

GRAPHQL_URL = 'https://api.sportvokrug.ru/graphql'
EVENT_ID = sys.argv[1] if len(sys.argv) > 1 else '15116'
OUT_DIR = sys.argv[2] if len(sys.argv) > 2 else '.'
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

QUERY = """
  query EventResultsByCategoryRG($event_id: ID!, $show_empty_categories: Boolean!) {
    eventResultsBycategoryRG(event_id: $event_id, showEmptyCategories: $show_empty_categories) {
      total filtered_total
      edges {
        category {
          id title discipline_id discipline_char_id
          score_names { id char_id title short_title }
        }
        applications {
          id rank final_total competitor_name
          team_name type_score is_reserve
          scores {
            ...on EventCompetitorScoreRG {
              apparatus apparatus_in_category score_index turn_num final_total rank
              is_dns is_dnf is_dsq dt_on_carpet
            }
          }
          athletes { id first_name last_name }
        }
      }
    }
  }
"""

def fetch_results():
    payload = json.dumps({
        'query': QUERY,
        'variables': {'event_id': EVENT_ID, 'show_empty_categories': False}
    }).encode('utf-8')
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={'Content-Type': 'application/json', 'Origin': 'https://www.sportvokrug.ru'}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8'))

APPARATUS_EN = {
    'обруч': 'hoop', 'мяч': 'ball', 'булавы': 'clubs', 'лента': 'ribbon',
    '5 мячей': '5 balls', '5 скакалок': '5 ropes',
    '3 обруча, 2 пары булав': '3 hoops, 2 pairs of clubs',
    '2 обруча, 3 булавы': '2 hoops, 3 clubs',
}

def build_categories(data):
    edges = data['data']['eventResultsBycategoryRG']['edges']
    categories = []
    latest_dt = None
    last_scored = None

    for edge in edges:
        cat = edge['category']
        apps = edge['applications']

        app_names = {}
        if cat.get('score_names'):
            for sn in cat['score_names']:
                sn['short_title'] = APPARATUS_EN.get(sn['short_title'], sn['short_title'])
                app_names[sn['char_id']] = sn['short_title']

        ranked = sorted([a for a in apps if a['rank'] is not None], key=lambda x: x['rank'])
        unranked = [a for a in apps if a['rank'] is None]
        competitors = []
        for app in (ranked if ranked else unranked):
            scores_by_app = {}
            for s in app['scores']:
                apparatus = s['apparatus']
                scores_by_app[apparatus] = {
                    'total': s['final_total'],
                    'rank': s['rank'],
                    'is_dns': s['is_dns'],
                    'is_dnf': s['is_dnf'],
                    'is_dsq': s['is_dsq'],
                }
                dt = s.get('dt_on_carpet')
                score_val = s['final_total']
                if dt and score_val and score_val > 0 and (latest_dt is None or dt > latest_dt):
                    latest_dt = dt
                    last_scored = {
                        'name': app['competitor_name'].strip(),
                        'team': app['team_name'] or '',
                        'apparatus': apparatus,
                        'apparatus_label': app_names.get(apparatus, apparatus),
                        'score': score_val,
                        'cat_id': cat['id'],
                    }
            competitors.append({
                'rank': app['rank'],
                'name': app['competitor_name'].strip(),
                'team': app['team_name'] or '',
                'final_total': app['final_total'],
                'scores': scores_by_app,
            })
        categories.append({
            'id': cat['id'],
            'title': cat['title'].strip(),
            'discipline': cat['discipline_char_id'],
            'score_names': cat['score_names'],
            'competitors': competitors,
            'has_results': len(ranked) > 0
        })
    return categories, last_scored

def generate_html(categories, last_scored):
    data_js = json.dumps(categories, ensure_ascii=False)
    last_scored_js = json.dumps(last_scored, ensure_ascii=False) if last_scored else 'null'
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

    with open(os.path.join(SCRIPT_DIR, 'index.html'), 'r') as f:
        content = f.read()

    import re
    content = re.sub(
        r'const CATEGORIES = \[.*?\];',
        f'const CATEGORIES = {data_js};',
        content, flags=re.DOTALL
    )
    content = re.sub(
        r'const LAST_SCORED = .*?;',
        f'const LAST_SCORED = {last_scored_js};',
        content, flags=re.DOTALL
    )
    content = re.sub(
        r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}',
        now_str, content
    )

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, 'index.html'), 'w') as f:
        f.write(content)

def run_once():
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Fetching results for event {EVENT_ID}...")
    data = fetch_results()
    categories, last_scored = build_categories(data)
    print(f"  {len(categories)} categories, last scored: {last_scored['name'] if last_scored else '—'}")
    generate_html(categories, last_scored)
    print(f"  index.html updated")

if __name__ == '__main__':
    import time
    watch = '--watch' in sys.argv

    run_once()
    if watch:
        print("Watching — press Ctrl+C to stop")
        while True:
            time.sleep(60)
            try:
                run_once()
            except Exception as e:
                print(f"  Error: {e}")
