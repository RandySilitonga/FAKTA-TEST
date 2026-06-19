"""
FAKTA - LSTM Inference Wrapper
Simple CLI for predicting hoax probability from text.
"""

import os
import sys
import argparse
from pathlib import Path

def predict(text: str, model_dir: str = "models/lstm") -> dict:
    """
    Predict hoax probability for a single text.

    Args:
        text: Input text
        model_dir: Directory containing lstm_model.keras and tokenizer.pkl

    Returns:
        Dict with hoax, valid, uncertain probabilities
    """
    import tensorflow as tf
    from tensorflow import keras
    import pickle

    model_path = os.path.join(model_dir, "lstm_model.keras")
    tokenizer_path = os.path.join(model_dir, "tokenizer.pkl")

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found at {model_path}")
    if not os.path.exists(tokenizer_path):
        raise FileNotFoundError(f"Tokenizer not found at {tokenizer_path}")

    # Load model and tokenizer
    model = keras.models.load_model(model_path)
    with open(tokenizer_path, "rb") as f:
        tokenizer = pickle.load(f)

    # Preprocess
    max_len = model.input_shape[1]
    seq = tokenizer.texts_to_sequences([text])
    padded = tf.keras.preprocessing.sequence.pad_sequences(
        seq, maxlen=max_len, padding="post", truncating="post"
    )

    # Predict
    predictions = model.predict(padded, verbose=0)
    probs = predictions[0]

    return {
        "valid": float(probs[0]),
        "hoax": float(probs[1]),
        "uncertain": float(probs[2]) if len(probs) > 2 else 0.0,
    }


def main():
    parser = argparse.ArgumentParser(description="FAKTA LSTM Predictor")
    parser.add_argument("text", help="Text to classify")
    parser.add_argument("--model-dir", default="models/lstm", help="Model directory")
    args = parser.parse_args()

    result = predict(args.text, args.model_dir)

    print(f"\nFAKTA LSTM Prediction:")
    print(f"  Hoax:     {result['hoax']:.4f}")
    print(f"  Valid:    {result['valid']:.4f}")
    print(f"  Uncertain: {result['uncertain']:.4f}")

    if result['hoax'] > 0.70:
        print(f"\n  Verdict: HOAX")
    elif result['hoax'] < 0.30:
        print(f"\n  Verdict: TIDAK HOAX")
    else:
        print(f"\n  Verdict: TIDAK CUKUP BUKTI")


if __name__ == "__main__":
    main()
