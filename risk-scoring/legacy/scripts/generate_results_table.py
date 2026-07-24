#!/usr/bin/env python3
"""
논문 형식 결과 표 생성 스크립트

MPOCryptoML 논문의 Table V 형식으로 결과를 정리

사용법:
    python scripts/generate_results_table.py
"""
import sys
import json
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def generate_latex_table(results: list, output_path: Path):
    """LaTeX 형식 표 생성 (논문 형식)"""
    latex_content = "\\begin{table}[h]\n"
    latex_content += "\\centering\n"
    latex_content += "\\caption{Model Performance Comparison}\n"
    latex_content += "\\label{tab:model_comparison}\n"
    latex_content += "\\begin{tabular}{lccccc}\n"
    latex_content += "\\toprule\n"
    latex_content += "Model & Pre@K & Recall@K & F1-score & ACC(\\%) & AUC(\\%) \\\\\n"
    latex_content += "\\midrule\n"
    
    # 논문 Baseline 모델들만 필터링 (우리 모델 + 논문 Baseline)
    paper_models = [
        "XGBoost", "DeepFD", "OCGTL", "ComGA", "Flowscope", 
        "GUDI", "MACE", "MPOCryptoML", "Hybrid"
    ]
    
    filtered_results = []
    for result in results:
        name = result["model_name"]
        # 논문 모델들만 포함
        if any(paper_model in name for paper_model in paper_models):
            filtered_results.append(result)
    
    # F1-Score 기준 정렬
    filtered_results.sort(key=lambda x: x['f1_score'], reverse=True)
    
    for result in filtered_results:
        name = result["model_name"]
        prec_at_k = result.get("precision_at_k", 0.0)
        recall_at_k = result.get("recall_at_k", 0.0)
        f1 = result["f1_score"]
        acc = result["accuracy"]
        auc = result["roc_auc"]
        
        # 모델 이름 간소화
        if "MPOCryptoML" in name:
            name = "\\textbf{MPOCryptoML}"
        elif "Hybrid" in name:
            name = "\\textbf{Hybrid}"
        elif "XGBoost" in name and "GUDI" not in name:
            name = "XGBoost"
        elif "DeepFD" in name:
            name = "DeepFD"
        elif "OCGTL" in name:
            name = "OCGTL"
        elif "ComGA" in name:
            name = "ComGA"
        elif "Flowscope" in name:
            name = "Flowscope"
        elif "GUDI" in name:
            name = "GUDI"
        elif "MACE" in name:
            name = "MACE"
        
        latex_content += f"{name} & {prec_at_k:.4f} & {recall_at_k:.4f} & {f1:.4f} & {acc:.4f} & {auc:.4f} \\\\\n"
    
    latex_content += "\\bottomrule\n"
    latex_content += "\\end{tabular}\n"
    latex_content += "\\end{table}\n"
    
    with open(output_path, 'w') as f:
        f.write(latex_content)
    
    print(f"✅ LaTeX 표 저장: {output_path}")


def generate_markdown_table(results: list, output_path: Path):
    """Markdown 형식 표 생성 (논문 형식)"""
    md_content = "# Model Performance Comparison (논문 형식)\n\n"
    md_content += "| Model | Pre@K | Recall@K | F1-score | ACC(%) | AUC(%) |\n"
    md_content += "|-------|-------|----------|----------|--------|--------|\n"
    
    # 논문 Baseline 모델들만 필터링
    paper_models = [
        "XGBoost", "DeepFD", "OCGTL", "ComGA", "Flowscope", 
        "GUDI", "MACE", "MPOCryptoML", "Hybrid"
    ]
    
    filtered_results = []
    for result in results:
        name = result["model_name"]
        if any(paper_model in name for paper_model in paper_models):
            filtered_results.append(result)
    
    # F1-Score 기준 정렬
    filtered_results.sort(key=lambda x: x['f1_score'], reverse=True)
    
    for result in filtered_results:
        name = result["model_name"]
        prec_at_k = result.get("precision_at_k", 0.0)
        recall_at_k = result.get("recall_at_k", 0.0)
        f1 = result["f1_score"]
        acc = result["accuracy"]
        auc = result["roc_auc"]
        
        # 모델 이름 간소화
        if "MPOCryptoML" in name:
            name = "**MPOCryptoML**"
        elif "Hybrid" in name:
            name = "**Hybrid**"
        elif "XGBoost" in name and "GUDI" not in name:
            name = "XGBoost"
        elif "DeepFD" in name:
            name = "DeepFD"
        elif "OCGTL" in name:
            name = "OCGTL"
        elif "ComGA" in name:
            name = "ComGA"
        elif "Flowscope" in name:
            name = "Flowscope"
        elif "GUDI" in name:
            name = "GUDI"
        elif "MACE" in name:
            name = "MACE"
        
        md_content += f"| {name} | {prec_at_k:.4f} | {recall_at_k:.4f} | {f1:.4f} | {acc:.4f} | {auc:.4f} |\n"
    
    with open(output_path, 'w') as f:
        f.write(md_content)
    
    print(f"✅ Markdown 표 저장: {output_path}")


def generate_csv_table(results: list, output_path: Path):
    """CSV 형식 표 생성 (논문 형식)"""
    import csv
    
    # 논문 Baseline 모델들만 필터링
    paper_models = [
        "XGBoost", "DeepFD", "OCGTL", "ComGA", "Flowscope", 
        "GUDI", "MACE", "MPOCryptoML", "Hybrid"
    ]
    
    filtered_results = []
    for result in results:
        name = result["model_name"]
        if any(paper_model in name for paper_model in paper_models):
            filtered_results.append(result)
    
    # F1-Score 기준 정렬
    filtered_results.sort(key=lambda x: x['f1_score'], reverse=True)
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Model', 'Pre@K', 'Recall@K', 'F1-score', 'ACC(%)', 'AUC(%)'])
        
        for result in filtered_results:
            name = result["model_name"]
            prec_at_k = result.get("precision_at_k", 0.0)
            recall_at_k = result.get("recall_at_k", 0.0)
            f1 = result["f1_score"]
            acc = result["accuracy"]
            auc = result["roc_auc"]
            
            # 모델 이름 간소화
            if "MPOCryptoML" in name:
                name = "MPOCryptoML"
            elif "Hybrid" in name:
                name = "Hybrid"
            elif "XGBoost" in name and "GUDI" not in name:
                name = "XGBoost"
            elif "DeepFD" in name:
                name = "DeepFD"
            elif "OCGTL" in name:
                name = "OCGTL"
            elif "ComGA" in name:
                name = "ComGA"
            elif "Flowscope" in name:
                name = "Flowscope"
            elif "GUDI" in name:
                name = "GUDI"
            elif "MACE" in name:
                name = "MACE"
            
            writer.writerow([name, f"{prec_at_k:.4f}", f"{recall_at_k:.4f}", f"{f1:.4f}", f"{acc:.4f}", f"{auc:.4f}"])
    
    print(f"✅ CSV 표 저장: {output_path}")


def generate_formatted_table(results: list):
    """포맷된 텍스트 표 출력"""
    print("\n" + "=" * 100)
    print("Model Performance Comparison (논문 형식)")
    print("=" * 100)
    
    # 헤더
    header = f"{'Model':<25} {'Accuracy':<12} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'ROC-AUC':<12} {'Avg Precision':<12}"
    print(header)
    print("-" * 100)
    
    # 결과 정렬 (F1-Score 기준)
    sorted_results = sorted(results, key=lambda x: x['f1_score'], reverse=True)
    
    for result in sorted_results:
        name = result["model_name"]
        acc = result["accuracy"]
        prec = result["precision"]
        rec = result["recall"]
        f1 = result["f1_score"]
        auc = result["roc_auc"]
        avg_prec = result["average_precision"]
        
        # 모델 이름 간소화
        if "MPOCryptoML" in name:
            name = "MPOCryptoML"
        elif "Hybrid" in name:
            name = "Hybrid"
        elif "Rule-based" in name:
            name = "Rule-based"
        elif "XGBoost" in name:
            name = "XGBoost"
        elif "Gradient Boosting" in name:
            name = "Gradient Boosting"
        elif "Random Forest" in name:
            name = "Random Forest"
        
        row = f"{name:<25} {acc:<12.4f} {prec:<12.4f} {rec:<12.4f} {f1:<12.4f} {auc:<12.4f} {avg_prec:<12.4f}"
        print(row)
    
    print("=" * 100)


def main():
    """메인 함수"""
    dataset_dir = project_root / "data" / "dataset"
    results_path = dataset_dir / "all_models_comparison.json"
    
    if not results_path.exists():
        print(f"❌ 결과 파일을 찾을 수 없습니다: {results_path}")
        print("   먼저 모델 비교를 실행하세요: python scripts/compare_all_models.py")
        return
    
    # 결과 로드
    with open(results_path, 'r') as f:
        results = json.load(f)
    
    print(f"📊 {len(results)}개 모델 결과 로드 완료")
    
    # 포맷된 표 출력 (논문 형식)
    print("\n" + "=" * 100)
    print("Model Performance Comparison (논문 형식 - Pre@K, Recall@K 포함)")
    print("=" * 100)
    
    # 논문 Baseline 모델들만 필터링
    paper_models = [
        "XGBoost", "DeepFD", "OCGTL", "ComGA", "Flowscope", 
        "GUDI", "MACE", "MPOCryptoML", "Hybrid"
    ]
    
    filtered_results = []
    for result in results:
        name = result["model_name"]
        if any(paper_model in name for paper_model in paper_models):
            filtered_results.append(result)
    
    # F1-Score 기준 정렬
    filtered_results.sort(key=lambda x: x['f1_score'], reverse=True)
    
    print(f"\n{'Model':<25} {'Pre@K':<12} {'Recall@K':<12} {'F1-Score':<12} {'ACC(%)':<12} {'AUC(%)':<12}")
    print("-" * 100)
    
    for result in filtered_results:
        name = result["model_name"]
        prec_at_k = result.get("precision_at_k", 0.0)
        recall_at_k = result.get("recall_at_k", 0.0)
        f1 = result["f1_score"]
        acc = result["accuracy"]
        auc = result["roc_auc"]
        
        # 모델 이름 간소화
        if "MPOCryptoML" in name:
            name = "MPOCryptoML"
        elif "Hybrid" in name:
            name = "Hybrid"
        elif "XGBoost" in name and "GUDI" not in name:
            name = "XGBoost"
        elif "DeepFD" in name:
            name = "DeepFD"
        elif "OCGTL" in name:
            name = "OCGTL"
        elif "ComGA" in name:
            name = "ComGA"
        elif "Flowscope" in name:
            name = "Flowscope"
        elif "GUDI" in name:
            name = "GUDI"
        elif "MACE" in name:
            name = "MACE"
        
        row = f"{name:<25} {prec_at_k:<12.4f} {recall_at_k:<12.4f} {f1:<12.4f} {acc:<12.4f} {auc:<12.4f}"
        print(row)
    
    print("=" * 100)
    
    # 전체 결과도 출력
    generate_formatted_table(results)
    
    # 다양한 형식으로 저장
    output_dir = project_root / "docs" / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # LaTeX 형식
    latex_path = output_dir / "model_comparison_table.tex"
    generate_latex_table(results, latex_path)
    
    # Markdown 형식
    md_path = output_dir / "model_comparison_table.md"
    generate_markdown_table(results, md_path)
    
    # CSV 형식
    csv_path = output_dir / "model_comparison_table.csv"
    generate_csv_table(results, csv_path)
    
    print(f"\n💾 모든 형식의 표가 저장되었습니다: {output_dir}")
    print("   - model_comparison_table.tex (LaTeX)")
    print("   - model_comparison_table.md (Markdown)")
    print("   - model_comparison_table.csv (CSV)")


if __name__ == "__main__":
    main()

