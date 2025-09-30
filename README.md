# Uplift Marketing Demo

В репозитории добавлены минимальные бэкенд и фронтенд, которые используют заранее обученные S-Learner модели для выбора лучшего предложения (Discount или Buy One Get One) либо рекомендации «No Offer».

## Структура

- `backend/` – FastAPI‑сервис, загружающий готовые модели из папки `Data/` и отдающий прогнозы по эндпоинту `/predict`.
- `frontend/` – статическая страница, отправляющая запросы к API и отображающая вероятности и uplift по каждому предложению.
- `Data/` – предоставленные pickle‑файлы моделей `s_learner_discount_model.pkl` и `s_learner_bogo_model.pkl`.

## Как запустить

1. **Установите зависимости для бэкенда** (понадобится Python ⩾ 3.9):

   ```powershell
   cd "c:\Users\Asus\Desktop\У\Applied_ML\backend"
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r ../requirements.txt
   ```

2. **Запустите API** (из папки backend):

   ```powershell
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

   Эндпоинт `/predict` принимает JSON вида:

   ```json
   {
     "recency": 5,
     "history": 2300,
     "zip_code": "Suburban",
     "channel": "Web",
     "is_referral": true,
     "used_discount": false,
     "used_bogo": true
   }
   ```

3. **Откройте фронтенд**. Можно запустить любой статический сервер. Например, встроенный из Python:

   ```powershell
   cd "c:\Users\Asus\Desktop\У\Applied_ML\frontend"
   python -m http.server 5173
   ```

   Затем перейдите на `http://127.0.0.1:5173` в браузере. По умолчанию скрипт обращается к `http://127.0.0.1:8000`. Чтобы сменить адрес, перед подключением скрипта добавьте в `index.html` строку:

   ```html
   <script>window.API_BASE_URL = "http://ваш-хост:порт";</script>
   ```

## Что делает API

1. Загружает сохранённые S-Learner пайплайны (каждый обучен на своём предложении против контрольной группы).
2. Для входных данных создаёт лог-признаки `recency_log`, `history_log` и формирует два набора: с `treat = 1` и `treat = 0`.
3. Считает вероятность конверсии с предложением и без него, затем uplift как разницу вероятностей.
4. Возвращает лучшую рекомендацию: если оба uplift ≤ 0, предлагается `No Offer`, иначе выбирается предложение с максимальным uplift.

Ответ API выглядит так:

```json
{
  "decision": {
    "best_offer": "Discount",
    "best_uplift": 0.0421,
    "uplift_discount": 0.0421,
    "uplift_bogo": -0.0053
  },
  "offers": {
    "Discount": {
      "treated_probability": 0.173,
      "control_probability": 0.131,
      "uplift": 0.0421
    },
    "Buy One Get One": {
      "treated_probability": 0.097,
      "control_probability": 0.102,
      "uplift": -0.0053
    }
  }
}
```

## Проверка

- [ ] Запуск и ручное тестирование API / фронтенда требуют установленного Python. В текущей среде `python` недоступен, поэтому автоматическая проверка не выполнялась.

## Возможные улучшения

- Добавить Docker-файл для унифицированного запуска.
- Вынести список допустимых категориальных значений в конфигурацию и подсвечивать их во фронтенде.
- Реализовать прогрев моделей и health-check эндпоинт.
