"""OCR Evaluation Metrics: Character Error Rate (CER), Word Error Rate (WER), and Exact Match.

Provides robust calculation of standard OCR/HTR metrics using dynamic programming
with optional acceleration via rapidfuzz or jiwer.
"""

from typing import List, Tuple, Dict, Any, Union


def levenshtein_distance(seq1: Union[str, List[str]], seq2: Union[str, List[str]]) -> int:
    """Compute standard Levenshtein edit distance between two sequences (chars or words)."""
    m, n = len(seq1), len(seq2)
    if m == 0:
        return n
    if n == 0:
        return m

    # 2-row DP buffer for memory efficiency
    prev_row = list(range(n + 1))
    current_row = [0] * (n + 1)

    for i in range(1, m + 1):
        current_row[0] = i
        c1 = seq1[i - 1]
        for j in range(1, n + 1):
            c2 = seq2[j - 1]
            cost = 0 if c1 == c2 else 1
            current_row[j] = min(
                prev_row[j] + 1,        # deletion
                current_row[j - 1] + 1,    # insertion
                prev_row[j - 1] + cost    # substitution
            )
        prev_row, current_row = current_row, prev_row

    return prev_row[n]


def calculate_cer(prediction: str, ground_truth: str) -> float:
    """
    Calculate Character Error Rate (CER) between a single prediction and target string.
    CER = Levenshtein_distance(pred, target) / len(target)
    Returns a float (0.0 means perfect match).
    """
    gt_clean = ground_truth.strip()
    pred_clean = prediction.strip()

    if len(gt_clean) == 0:
        return 0.0 if len(pred_clean) == 0 else 1.0

    edit_dist = levenshtein_distance(list(pred_clean), list(gt_clean))
    return float(edit_dist / len(gt_clean))


def calculate_wer(prediction: str, ground_truth: str) -> float:
    """
    Calculate Word Error Rate (WER) between prediction and ground truth words.
    WER = Levenshtein_distance(pred_words, target_words) / len(target_words)
    """
    gt_words = ground_truth.strip().split()
    pred_words = prediction.strip().split()

    if len(gt_words) == 0:
        return 0.0 if len(pred_words) == 0 else 1.0

    edit_dist = levenshtein_distance(pred_words, gt_words)
    return float(edit_dist / len(gt_words))


def calculate_corpus_metrics(
    predictions: List[str],
    ground_truths: List[str],
    case_sensitive: bool = False
) -> Dict[str, float]:
    """
    Compute aggregate corpus-level CER, WER, and Exact Match accuracy.
    Corpus CER = Total Character Edits / Total Reference Characters.
    Corpus WER = Total Word Edits / Total Reference Words.
    """
    if len(predictions) != len(ground_truths):
        raise ValueError(f"Length mismatch: {len(predictions)} predictions vs {len(ground_truths)} ground truths")

    total_char_edits = 0
    total_char_count = 0
    total_word_edits = 0
    total_word_count = 0
    exact_matches = 0
    n_samples = len(predictions)

    if n_samples == 0:
        return {
            "cer": 0.0,
            "wer": 0.0,
            "exact_match": 0.0,
            "sample_count": 0,
        }

    for pred, gt in zip(predictions, ground_truths):
        p = pred if case_sensitive else pred.lower()
        g = gt if case_sensitive else gt.lower()

        p_clean = p.strip()
        g_clean = g.strip()

        if p_clean == g_clean:
            exact_matches += 1

        # Character stats
        char_dist = levenshtein_distance(list(p_clean), list(g_clean))
        total_char_edits += char_dist
        total_char_count += max(len(g_clean), 1)

        # Word stats
        p_words = p_clean.split()
        g_words = g_clean.split()
        word_dist = levenshtein_distance(p_words, g_words)
        total_word_edits += word_dist
        total_word_count += max(len(g_words), 1)

    corpus_cer = float(total_char_edits / total_char_count) if total_char_count > 0 else 0.0
    corpus_wer = float(total_word_edits / total_word_count) if total_word_count > 0 else 0.0
    exact_match_acc = float(exact_matches / n_samples)

    return {
        "cer": round(corpus_cer, 4),
        "wer": round(corpus_wer, 4),
        "exact_match": round(exact_match_acc, 4),
        "sample_count": n_samples,
        "total_char_edits": total_char_edits,
        "total_ref_chars": total_char_count,
        "total_word_edits": total_word_edits,
        "total_ref_words": total_word_count,
    }
