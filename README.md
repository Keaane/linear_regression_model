# Crop Yield Prediction – Linear Regression Model

## Mission

My mission is to harness technology for positive impact, promoting human well-being and sustainable practices while minimizing negative consequences. This project applies machine learning to predict crop yields, helping farmers and policymakers make data-driven decisions that support food security and sustainable agriculture.

---

## Dataset

[Crop Yield Prediction Dataset – Kaggle](https://www.kaggle.com/)

---

## API Endpoint

Test predictions via Swagger UI:
[https://crop-yield-predictor-api-nhma.onrender.com/docs](https://crop-yield-predictor-api-nhma.onrender.com/docs)

---

## Video Demo

> 

---

## Project Structure
```
linear_regression_model/
├── summative/
│   ├── linear_regression/
│   │   └── multivariate.ipynb
│   ├── API/
│   │   ├── prediction.py
│   │   └── requirements.txt
│   └── FlutterApp/
```

---

## Running the Mobile App

**Prerequisites:** Flutter SDK installed ([flutter.dev](https://flutter.dev))
```bash
# Clone the repo
git clone https://github.com/Keaane/linear_regression_model
cd linear_regression_model/summative/FlutterApp

# Install dependencies
flutter pub get

# Run on a connected device or emulator
flutter run
```

The app will connect to the live API automatically. Enter **country**, **crop type**, **year**, **rainfall**, **temperature**, and **pesticide** values, then tap **Predict** to see the estimated yield.
