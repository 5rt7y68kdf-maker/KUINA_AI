import os
import glob
import json
import pandas as pd
import time

def convert_past_races_to_json(output_json="past_index.json"):
    print("=== 過去走CSV -> 軽量JSONインデックス変換開始 ===")
    start_time = time.time()
    
    # 過去走CSVを検索 (例: 2026過去走1.csv 〜 2026過去走10.csv)
    search_patterns = [
        "./*過去走*.csv", "./*過去走*.CSV",
        "./data/*過去走*.csv", "./data/*過去走*.CSV"
    ]
    
    past_files = []
    for pat in search_patterns:
        past_files.extend(glob.glob(pat))
    past_files = sorted(list(set(past_files)))
    
    if not past_files:
        print("⚠️ 過去走CSVが見つかりません。『2026過去走1.csv』などを同じフォルダに配置して実行してください。")
        return
    
    print(f"対象ファイル ({len(past_files)}件): {[os.path.basename(f) for f in past_files]}")
    
    horse_past_map = {}
    
    for fpath in past_files:
        print(f"処理中: {os.path.basename(fpath)}...")
        df = None
        for enc in ["cp932", "shift_jis", "utf-8"]:
            try:
                df = pd.read_csv(fpath, encoding=enc, dtype=str, on_bad_lines="skip")
                break
            except Exception:
                pass
        
        if df is None or df.empty or "馬名" not in df.columns:
            print(f"  -> スキップ (無効な形式または馬名列なし)")
            continue
        
        cols = ["馬名", "通過1", "馬場状態", "着順", "上り3F順位", "PCI", "クラス", "前走クラス", "着差", "距離"]
        existing_cols = [c for c in cols if c in df.columns]
        df_sub = df[existing_cols].copy()
        
        for row in df_sub.to_dict("records"):
            h_name = str(row.get("馬名", "")).strip()
            if not h_name:
                continue
            
            if h_name not in horse_past_map:
                horse_past_map[h_name] = []
            
            # 馬ごとに最新5走分のみを保持（容量・メモリを大幅削減）
            if len(horse_past_map[h_name]) < 5:
                horse_past_map[h_name].append({
                    "通過1": str(row.get("通過1", "")),
                    "馬場状態": str(row.get("馬場状態", "良")),
                    "着順": str(row.get("着順", "99")),
                    "上り3F順位": str(row.get("上り3F順位", "99")),
                    "PCI": str(row.get("PCI", "50.0")),
                    "クラス": str(row.get("クラス", row.get("前走クラス", ""))),
                    "着差": str(row.get("着差", "0.5")),
                    "距離": str(row.get("距離", "1800")),
                })

    # 軽量JSONとして保存
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(horse_past_map, f, ensure_ascii=False, separators=(',', ':'))
    
    file_size_mb = os.path.getsize(output_json) / (1024 * 1024)
    elapsed = time.time() - start_time
    print(f"\n✅ 完了! '{output_json}' を作成しました。")
    print(f"  ・ 登録馬数: {len(horse_past_map)} 頭")
    print(f"  ・ 生成サイズ: {file_size_mb:.2f} MB")
    print(f"  ・ 処理時間: {elapsed:.2f} 秒")

if __name__ == "__main__":
    convert_past_races_to_json()
