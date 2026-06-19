"""
FAKTA - LSTM Model Definition
3-class LSTM classifier: hoax, valid, uncertain.
Input: full article text (not just extracted claims).
"""

import os
from typing import Optional, Tuple, Dict
import numpy as np


def build_lstm_model(
    max_words: int = 20000,
    max_len: int = 200,
    embedding_dim: int = 128,
    lstm_units: int = 64,
    dropout_rate: float = 0.3,
    num_classes: int = 3,
    use_bidirectional: bool = True,
) -> "keras.Model":
    """
    Build LSTM model for hoax classification.

    Args:
        max_words: Vocabulary size
        max_len: Maximum sequence length (padding)
        embedding_dim: Embedding dimension
        lstm_units: Number of LSTM units
        dropout_rate: Dropout rate
        num_classes: Number of output classes (hoax, valid, uncertain)
        use_bidirectional: Whether to use BiLSTM

    Returns:
        Compiled Keras model
    """
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import (
        Embedding, LSTM, Bidirectional, Dense,
        Dropout, GlobalMaxPooling1D, Input, concatenate,
    )

    model = Sequential([
        Embedding(
            input_dim=max_words,
            output_dim=embedding_dim,
            input_length=max_len,
            mask_zero=True,
        ),
        Dropout(dropout_rate),
    ])

    if use_bidirectional:
        model.add(Bidirectional(
            LSTM(lstm_units, return_sequences=True, dropout=dropout_rate)
        ))
        model.add(Bidirectional(
            LSTM(lstm_units // 2, return_sequences=False)
        ))
    else:
        model.add(LSTM(lstm_units, return_sequences=True, dropout=dropout_rate))
        model.add(LSTM(lstm_units // 2, return_sequences=False))

    model.add(Dense(32, activation="relu"))
    model.add(Dropout(dropout_rate))
    model.add(Dense(num_classes, activation="softmax"))

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

    return model


def build_lstm_with_features(
    max_words: int = 20000,
    max_len: int = 200,
    embedding_dim: int = 128,
    lstm_units: int = 64,
    dropout_rate: float = 0.3,
    num_classes: int = 3,
    num_metadata_features: int = 14,
) -> "keras.Model":
    """
    Build LSTM model with additional linguistic features as a second input branch.

    This fuses the LSTM text embedding output with hand-crafted linguistic features
    (caps_ratio, provocative_word_count, etc.) before the final classification layer.
    """
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras.layers import (
        Embedding, LSTM, Bidirectional, Dense,
        Dropout, Input, concatenate,
    )
    from tensorflow.keras.models import Model

    # Text branch
    text_input = Input(shape=(max_len,), dtype="int32", name="text_input")
    x = Embedding(
        input_dim=max_words,
        output_dim=embedding_dim,
        input_length=max_len,
        mask_zero=True,
    )(text_input)
    x = Dropout(dropout_rate)(x)
    x = Bidirectional(LSTM(lstm_units, return_sequences=True, dropout=dropout_rate))(x)
    x = Bidirectional(LSTM(lstm_units // 2, return_sequences=False))(x)
    text_output = Dense(64, activation="relu")(x)
    text_output = Dropout(dropout_rate)(text_output)

    # Metadata features branch
    feature_input = Input(shape=(num_metadata_features,), dtype="float32", name="feature_input")
    feature_output = Dense(32, activation="relu")(feature_input)
    feature_output = Dropout(dropout_rate * 0.5)(feature_output)

    # Concatenate both branches
    combined = concatenate([text_output, feature_output])
    combined = Dense(32, activation="relu")(combined)
    combined = Dropout(dropout_rate)(combined)
    output = Dense(num_classes, activation="softmax", name="output")(combined)

    model = Model(inputs=[text_input, feature_input], outputs=output)

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

    return model


class LSTMPredictor:
    """Wrapper for LSTM inference."""

    LABELS = ["valid", "hoax", "uncertain"]  # index matches class index

    def __init__(self, model_path: str, max_len: int = 200, max_words: int = 20000):
        import tensorflow as tf
        from tensorflow import keras
        self.max_len = max_len
        self.max_words = max_words
        self.model = keras.models.load_model(model_path)
        self.tokenizer = None
        self._load_tokenizer(model_path)

    def _load_tokenizer(self, model_path: str):
        """Load the tokenizer saved alongside the model."""
        import pickle
        tokenizer_path = model_path.replace(".keras", "_tokenizer.pkl").replace(".h5", "_tokenizer.pkl")
        if os.path.exists(tokenizer_path):
            with open(tokenizer_path, "rb") as f:
                self.tokenizer = pickle.load(f)

    def predict(self, text: str) -> Dict[str, float]:
        """
        Predict hoax probability for a single text.

        Returns:
            {"hoax": 0.xx, "valid": 0.xx, "uncertain": 0.xx}
        """
        import tensorflow as tf
        if self.tokenizer is None:
            return {"hoax": 0.5, "valid": 0.25, "uncertain": 0.25}  # fallback

        seq = self.tokenizer.texts_to_sequences([text])
        padded = tf.keras.preprocessing.sequence.pad_sequences(
            seq, maxlen=self.max_len, padding="post", truncating="post"
        )

        predictions = self.model.predict(padded, verbose=0)
        probs = predictions[0]

        return {
            "hoax": float(probs[1]) if len(probs) > 1 else 0.0,
            "valid": float(probs[0]) if len(probs) > 0 else 0.0,
            "uncertain": float(probs[2]) if len(probs) > 2 else 0.0,
        }


if __name__ == "__main__":
    model = build_lstm_model()
    model.summary()
    print(f"\nTotal params: {model.count_params():,}")
