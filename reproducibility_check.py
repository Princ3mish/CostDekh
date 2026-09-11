import os
import shutil
import subprocess
import sys
import pandas as pd

if __name__ == '__main__':
    pipeline_scripts = [
        os.path.join('backend', 'pipeline', 'aggregate.py'),
        os.path.join('backend', 'pipeline', 'compare.py'),
        os.path.join('backend', 'pipeline', 'notes_retrieval.py'),
        os.path.join('backend', 'pipeline', 'explanation.py'),
        os.path.join('backend', 'pipeline', 'finalize.py')
    ]

    for run_idx in range(1, 4):
        for script in pipeline_scripts:
            subprocess.run([sys.executable, script], check=True)
        shutil.copy(
            os.path.join('output', 'final_flagged_routes.csv'),
            os.path.join('output', f'run_{run_idx}.csv')
        )

    cols_to_compare = [
        'route', 'week_of', 'cost_per_tonne_km', 'vs_own_history',
        'vs_similar_routes', 'flagged', 'matched_note_id'
    ]

    df1 = pd.read_csv(os.path.join('output', 'run_1.csv'), keep_default_na=False)[cols_to_compare]
    df2 = pd.read_csv(os.path.join('output', 'run_2.csv'), keep_default_na=False)[cols_to_compare]
    df3 = pd.read_csv(os.path.join('output', 'run_3.csv'), keep_default_na=False)[cols_to_compare]

    match_1_2 = df1.equals(df2)
    match_2_3 = df2.equals(df3)

    if match_1_2 and match_2_3:
        print("REPRODUCIBLE")
    else:
        if not match_1_2:
            diff12 = df1.compare(df2)
            print(f"Diff between Run 1 and Run 2:\n{diff12}")
        if not match_2_3:
            diff23 = df2.compare(df3)
            print(f"Diff between Run 2 and Run 3:\n{diff23}")
