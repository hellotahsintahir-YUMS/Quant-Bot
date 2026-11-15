"""LSTM forecasting signal for Quant Bot.

TensorFlow is imported lazily so the existing technical-indicator mode does
not require the optional ML dependency.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class LSTMForecast:
    prediction: float
    last_price: float
    expected_return: float
    action: str
    confidence: float


class LSTMForecaster:
    """Train a compact Keras LSTM and produce a one-step forecast."""

    def __init__(
        self,
        sequence_length: int = 50,
        lookahead: int = 1,
        epochs: int = 10,
        batch_size: int = 32,
        units: tuple[int, int, int] = (64, 64, 32),
        learning_rate: float = 1e-3,
        seed: int = 42,
    ):
        self.sequence_length = sequence_length
        self.lookahead = lookahead
        self.epochs = epochs
        self.batch_size = batch_size
        self.units = units
        self.learning_rate = learning_rate
        self.seed = seed
        self._model = None
        self._scaler = None

    @staticmethod
    def _mid_price(data: pd.DataFrame) -> np.ndarray:
        if {"High", "Low"}.issubset(data.columns):
            values = ((data["High"] + data["Low"]) / 2.0).to_numpy(dtype=float)
        elif "Close" in data.columns:
            values = data["Close"].to_numpy(dtype=float)
        else:
            raise ValueError("LSTM data must contain High/Low or Close columns")
        values = values[np.isfinite(values)]
        if len(values) == 0 or np.any(values <= 0):
            raise ValueError("LSTM data contains no valid positive prices")
        return values

    def _make_sequences(self, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        if len(values) <= self.sequence_length + self.lookahead:
            raise ValueError(
                f"Need more than {self.sequence_length + self.lookahead} price points "
                f"to train the LSTM; received {len(values)}"
            )
        x, y = [], []
        end = len(values) - self.lookahead
        for index in range(end - self.sequence_length):
            x.append(values[index:index + self.sequence_length])
            y.append(values[index + self.sequence_length + self.lookahead - 1])
        return np.asarray(x)[..., np.newaxis], np.asarray(y)

    def fit(self, data: pd.DataFrame) -> "LSTMForecaster":
        try:
            import tensorflow as tf
            from sklearn.preprocessing import MinMaxScaler
        except ImportError as exc:
            raise RuntimeError(
                "LSTM mode requires TensorFlow. Install dependencies with "
                "`pip install -r requirements.txt`."
            ) from exc

        tf.keras.utils.set_random_seed(self.seed)
        prices = self._mid_price(data)
        self._scaler = MinMaxScaler()
        scaled = self._scaler.fit_transform(prices.reshape(-1, 1)).ravel()
        x, y = self._make_sequences(scaled)

        model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(self.sequence_length, 1)),
            tf.keras.layers.LSTM(self.units[0], return_sequences=True, dropout=0.2),
            tf.keras.layers.LSTM(self.units[1], return_sequences=True, dropout=0.2),
            tf.keras.layers.LSTM(self.units[2], dropout=0.2),
            tf.keras.layers.Dense(1),
        ])
        optimizer = tf.keras.optimizers.Adam(
            learning_rate=self.learning_rate, clipnorm=5.0
        )
        model.compile(optimizer=optimizer, loss="mse")
        validation_size = max(1, int(len(x) * 0.2))
        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss", patience=2, restore_best_weights=True
            )
        ]
        model.fit(
            x[:-validation_size],
            y[:-validation_size],
            validation_data=(x[-validation_size:], y[-validation_size:]),
            epochs=self.epochs,
            batch_size=min(self.batch_size, len(x)),
            shuffle=False,
            callbacks=callbacks,
            verbose=0,
        )
        self._model = model
        return self

    def forecast(self, data: pd.DataFrame) -> LSTMForecast:
        if self._model is None or self._scaler is None:
            raise RuntimeError("Fit the LSTM before forecasting")
        prices = self._mid_price(data)
        if len(prices) < self.sequence_length:
            raise ValueError(
                f"Need {self.sequence_length} prices to forecast; received {len(prices)}"
            )
        scaled = self._scaler.transform(prices.reshape(-1, 1)).ravel()
        window = scaled[-self.sequence_length:].reshape(1, self.sequence_length, 1)
        prediction = float(self._scaler.inverse_transform(
            self._model.predict(window, verbose=0)
        )[0, 0])
        last_price = float(prices[-1])
        expected_return = (prediction - last_price) / last_price
        threshold = 0.005
        action = "BUY" if expected_return > threshold else (
            "SELL" if expected_return < -threshold else "HOLD"
        )
        confidence = float(np.clip(abs(expected_return) / 0.02, 0.0, 1.0))
        return LSTMForecast(
            prediction=prediction,
            last_price=last_price,
            expected_return=expected_return,
            action=action,
            confidence=confidence,
        )
