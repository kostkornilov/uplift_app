const API_BASE_URL = window.API_BASE_URL || "http://127.0.0.1:8000";

const form = document.getElementById("uplift-form");
const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");
const resultTemplate = document.getElementById("result-template");

function formatProbability(value) {
    return `${(value * 100).toFixed(2)}%`;
}

function toggleLoading(isLoading) {
    const button = form.querySelector("button[type='submit']");
    button.disabled = isLoading;
    button.textContent = isLoading ? "Рассчитываем..." : "Получить рекомендацию";
}

function buildPayload(formData) {
    return {
        recency: Number(formData.get("recency")),
        history: Number(formData.get("history")),
        zip_code: formData.get("zip_code")?.trim(),
        channel: formData.get("channel"),
        is_referral: formData.get("is_referral") === "on",
        used_discount: formData.get("used_discount") === "on",
        used_bogo: formData.get("used_bogo") === "on",
    };
}

function renderResult(response) {
    resultEl.innerHTML = "";
    const clone = resultTemplate.content.cloneNode(true);

    clone.querySelector("[data-best-offer]").textContent = response.decision.best_offer;

    clone.querySelector("[data-discount-treated]").textContent = formatProbability(
        response.offers["Discount"].treated_probability
    );
    clone.querySelector("[data-discount-control]").textContent = formatProbability(
        response.offers["Discount"].control_probability
    );
    clone.querySelector("[data-discount-uplift]").textContent = formatProbability(
        response.offers["Discount"].uplift
    );

    clone.querySelector("[data-bogo-treated]").textContent = formatProbability(
        response.offers["Buy One Get One"].treated_probability
    );
    clone.querySelector("[data-bogo-control]").textContent = formatProbability(
        response.offers["Buy One Get One"].control_probability
    );
    clone.querySelector("[data-bogo-uplift]").textContent = formatProbability(
        response.offers["Buy One Get One"].uplift
    );

    resultEl.appendChild(clone);
    resultEl.classList.remove("hidden");
}

async function sendRequest(payload) {
    const response = await fetch(`${API_BASE_URL}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const text = await response.text();
        throw new Error(text || "Ошибка запроса к API");
    }

    return response.json();
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    resultEl.classList.add("hidden");
    statusEl.textContent = "Отправляем запрос к модели...";

    const formData = new FormData(form);
    const payload = buildPayload(formData);

    toggleLoading(true);
    try {
        const data = await sendRequest(payload);
        statusEl.textContent = "";
        renderResult(data);
    } catch (error) {
        console.error(error);
        statusEl.textContent = error.message || "Не удалось получить результат. Попробуйте снова.";
    } finally {
        toggleLoading(false);
    }
});
