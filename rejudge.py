"""Chấm lại câu trả lời đã lưu bằng judge khác, KHÔNG chạy lại agent.

Dùng grade_case/summarize nguyên bản từ evals/grading.py; chỉ đổi judge.
Ví dụ:
  python3 rejudge.py eval_after.json --judge-provider openai --judge-model gpt-6-luna --output rejudge_after_luna.json
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'evals'))
from grading import grade_case, summarize
from providers import Provider


def main():
    p = argparse.ArgumentParser(description='Chấm lại kết quả eval đã lưu bằng judge khác')
    p.add_argument('input', help='File eval đã có, ví dụ eval_after.json')
    p.add_argument('--judge-provider', required=True, choices=['openai', 'gemini', 'anthropic', 'openrouter'])
    p.add_argument('--judge-model', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()

    report = json.loads(Path(args.input).read_text())
    cases = {c['id']: c for c in json.loads((ROOT / 'evals' / 'cases.json').read_text())}
    judge = Provider(args.judge_provider, args.judge_model)

    results = []
    for item in report['cases']:
        case = cases[item['id']]  # case gốc để mechanical checks giống hệt run_evals
        try:
            grade = grade_case(case, item['result'], judge)
        except Exception as exc:
            grade = {'score': None, 'status': 'unscored', 'reason': str(exc), 'judge_usage': {}}
        old = item['grade'].get('score')
        print(f"{item['id']}: {old} -> {grade.get('score')} ({grade['status']})", flush=True)
        results.append({**item, 'judge_provider': args.judge_provider, 'judge_model': args.judge_model,
                        'grade': grade, 'original_grade': item['grade']})

    out = {'summary': summarize(results),
           'config': {**report['config'], 'judge_provider': args.judge_provider, 'judge_model': args.judge_model,
                      'rejudged_from': args.input, 'original_judge': report['config'].get('judge_model')},
           'original_summary': report['summary'], 'cases': results}
    Path(args.output).write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
    s = out['summary']
    print(f"Gốc ({out['config']['original_judge']}): {report['summary'].get('score_0_100')} | "
          f"Chấm lại ({args.judge_model}): {s['score_0_100']}; đã chấm {s['scored_cases']}/{s['total_cases']}. File: {args.output}")


if __name__ == '__main__':
    main()
