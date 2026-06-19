"""
FAKTA - LSTM Training Script
Trains the LSTM classifier on collected hoax dataset.
"""

import os
import sys
import pickle
import yaml
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_class_weight


def load_dataset(data_dir: str) -> pd.DataFrame:
    """
    Load training dataset from CSV files in data_dir.

    Expected columns: text, label, source
    Labels: hoax, valid, uncertain
    """
    files = list(Path(data_dir).glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")

    dfs = []
    for f in files:
        df = pd.read_csv(f)
        if "text" not in df.columns or "label" not in df.columns:
            print(f"Skipping {f}: missing text or label column")
            continue
        dfs.append(df[["text", "label"]])

    if not dfs:
        raise ValueError("No valid datasets found")

    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.dropna(subset=["text", "label"])
    combined["label"] = combined["label"].str.lower().str.strip()
    combined = combined[combined["label"].isin(["hoax", "valid", "uncertain"])]

    print(f"Loaded {len(combined)} samples:")
    print(combined["label"].value_counts())

    return combined


def prepare_sequences(
    texts: list,
    labels: list,
    max_words: int = 20000,
    max_len: int = 200,
):
    """
    Tokenize texts and pad sequences. Returns tokenizer, X, y.
    """
    import tensorflow as tf
    from tensorflow.keras.preprocessing.text import Tokenizer
    from tensorflow.keras.preprocessing.sequence import pad_sequences

    tokenizer = Tokenizer(num_words=max_words, oov_token="<OOV>")
    tokenizer.fit_on_texts(texts)

    sequences = tokenizer.texts_to_sequences(texts)
    X = pad_sequences(sequences, maxlen=max_len, padding="post", truncating="post")

    label_map = {"valid": 0, "hoax": 1, "uncertain": 2}
    y = np.array([label_map[l] for l in labels])

    return tokenizer, X, y


def train_model(
    data_dir: str,
    model_dir: str,
    config_path: str = "configs/lstm_config.yaml",
):
    """
    Full training pipeline.
    """
    import tensorflow as tf
    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

    # Load config
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = yaml.safe_load(f)
    else:
        config = {}

    max_words = config.get("max_words", 20000)
    max_len = config.get("max_len", 200)
    embedding_dim = config.get("embedding_dim", 128)
    lstm_units = config.get("lstm_units", 64)
    dropout_rate = config.get("dropout_rate", 0.3)
    epochs = config.get("epochs", 20)
    batch_size = config.get("batch_size", 64)

    # Load data
    print("Loading dataset...")
    df = load_dataset(data_dir)

    # Split
    train_df, test_df = train_test_split(
        df, test_size=0.15, random_state=42, stratify=df["label"]
    )
    train_df, val_df = train_test_split(
        train_df, test_size=0.18, random_state=42, stratify=train_df["label"]
    )

    print(f"Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")

    # Prepare sequences
    tokenizer, X_train, y_train = prepare_sequences(
        train_df["text"].tolist(), train_df["label"].tolist(),
        max_words=max_words, max_len=max_len,
    )
    _, X_val, y_val = prepare_sequences(
        val_df["text"].tolist(), val_df["label"].tolist(),
        max_words=max_words, max_len=max_len,
    )
    _, X_test, y_test = prepare_sequences(
        test_df["text"].tolist(), test_df["label"].tolist(),
        max_words=max_words, max_len=max_len,
    )

    # Class weights (handle imbalance)
    classes = np.unique(y_train)
    weights = compute_class_weight("balanced", classes=classes, y=y_train)
    class_weight = dict(zip(classes, weights))
    print(f"Class weights: {class_weight}")

    # Build model
    from lstm_model import build_lstm_model
    model = build_lstm_model(
        max_words=max_words,
        max_len=max_len,
        embedding_dim=embedding_dim,
        lstm_units=lstm_units,
        dropout_rate=dropout_rate,
    )

    # Callbacks
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "lstm_model.keras")
    tokenizer_path = os.path.join(model_dir, "tokenizer.pkl")

    callbacks = [
        EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True),
        ModelCheckpoint(model_path, save_best_only=True, monitor="val_loss"),
    ]

    # Train
    print("Training...")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        class_weight=class_weight,
        callbacks=callbacks,
    )

    # Save tokenizer
    with open(tokenizer_path, "wb") as f:
        pickle.dump(tokenizer, f)

    # Evaluate
    print("\nTest set evaluation:")
    loss, accuracy = model.evaluate(X_test, y_test, verbose=0)
    print(f"Test Loss: {loss:.4f}, Test Accuracy: {accuracy:.4f}")

    # Classification report
    from sklearn.metrics import classification_report
    y_pred = np.argmax(model.predict(X_test), axis=1)
    label_names = ["valid", "hoax", "uncertain"]
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=label_names))

    print(f"\nModel saved to {model_path}")
    print(f"Tokenizer saved to {tokenizer_path}")

    return model, history


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data/training"
    model_dir = sys.argv[2] if len(sys.argv) > 2 else "models/lstm"
    train_model(data_dir, model_dir)
