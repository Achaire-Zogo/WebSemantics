document.addEventListener('DOMContentLoaded', function() {
    // Gestion des tabs
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(tc => tc.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(btn.dataset.tab).classList.add('active');
        });
    });

    // Recherche Google-like
    const form = document.getElementById('searchForm');
    const input = document.getElementById('searchInput');
    const resultsSection = document.getElementById('resultsSection');
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        const query = input.value.trim();
        if (!query) return;
        resultsSection.innerHTML = '<p>Recherche en cours...</p>';
        try {
            const url = `http://localhost:8080/api/search?q=${encodeURIComponent(query)}`;
            const response = await fetch(url);
            if (!response.ok) throw new Error('Erreur lors de la requête');
            const data = await response.json();
            afficherMessage(resultsSection, data.message);
            afficherResultats(resultsSection, data.results);
        } catch (err) {
            resultsSection.innerHTML = `<p style=\"color:red;\">${err.message}</p>`;
        }
    });

    // Tous les repas
    const showAllBtn = document.getElementById('showAllBtn');
    const allFoodsSection = document.getElementById('allFoodsSection');
    showAllBtn.addEventListener('click', async function() {
        allFoodsSection.innerHTML = '<p>Chargement de tous les aliments...</p>';
        try {
            const url = 'http://localhost:8080/api/foods/all';
            const response = await fetch(url);
            if (!response.ok) throw new Error('Erreur lors de la requête');
            const data = await response.json();
            afficherMessage(allFoodsSection, data.message);
            afficherResultats(allFoodsSection, data.results);
        } catch (err) {
            allFoodsSection.innerHTML = `<p style=\"color:red;\">${err.message}</p>`;
        }
    });

    // Image principale d'un aliment
    const imageForm = document.getElementById('imageForm');
    const imageFoodInput = document.getElementById('imageFoodInput');
    const imageResult = document.getElementById('imageResult');
    imageForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const food = imageFoodInput.value.trim();
        if (!food) return;
        imageResult.innerHTML = '<p>Chargement...</p>';
        try {
            const url = `http://localhost:8080/api/food/${encodeURIComponent(food)}/image`;
            const response = await fetch(url);
            if (!response.ok) throw new Error('Aucune image trouvée pour cet aliment.');
            const blob = await response.blob();
            const imgUrl = URL.createObjectURL(blob);
            imageResult.innerHTML = `<img src="${imgUrl}" alt="${food}" style="max-width:300px;border-radius:8px;">`;
        } catch (err) {
            imageResult.innerHTML = `<p style=\"color:red;\">${err.message}</p>`;
        }
    });

    // Image par index
    const imageIndexForm = document.getElementById('imageIndexForm');
    const imageIndexFoodInput = document.getElementById('imageIndexFoodInput');
    const imageIndexInput = document.getElementById('imageIndexInput');
    const imageIndexResult = document.getElementById('imageIndexResult');
    imageIndexForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const food = imageIndexFoodInput.value.trim();
        const idx = imageIndexInput.value.trim();
        if (!food || idx === '') return;
        imageIndexResult.innerHTML = '<p>Chargement...</p>';
        try {
            const url = `http://localhost:8080/api/food/${encodeURIComponent(food)}/image/${idx}`;
            const response = await fetch(url);
            if (!response.ok) throw new Error('Aucune image trouvée pour cet aliment ou cet index.');
            const blob = await response.blob();
            const imgUrl = URL.createObjectURL(blob);
            imageIndexResult.innerHTML = `<img src="${imgUrl}" alt="${food} [${idx}]" style="max-width:300px;border-radius:8px;">`;
        } catch (err) {
            imageIndexResult.innerHTML = `<p style=\"color:red;\">${err.message}</p>`;
        }
    });

    // Suggestions de recherche
    const suggestForm = document.getElementById('suggestForm');
    const suggestInput = document.getElementById('suggestInput');
    const suggestResult = document.getElementById('suggestResult');
    suggestForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const query = suggestInput.value.trim();
        if (!query) return;
        suggestResult.innerHTML = '<p>Chargement...</p>';
        try {
            const url = `http://localhost:8080/api/search/suggest?q=${encodeURIComponent(query)}`;
            const response = await fetch(url);
            if (!response.ok) throw new Error('Erreur lors de la requête');
            const data = await response.json();
            if (data.suggestions && data.suggestions.length) {
                suggestResult.innerHTML = '<ul>' + data.suggestions.map(s => {
                    if (typeof s === 'string') return `<li>${s}</li>`;
                    if (typeof s === 'object' && s !== null) return `<li>${s.suggestion || s.name || s.label || Object.values(s)[0]}</li>`;
                    return `<li>${s}</li>`;
                }).join('') + '</ul>';
            } else {
                suggestResult.innerHTML = '<p>Aucune suggestion trouvée.</p>';
            }
        } catch (err) {
            suggestResult.innerHTML = `<p style=\"color:red;\">${err.message}</p>`;
        }
    });

    // Fonctions utilitaires d'affichage
    function afficherMessage(section, message) {
        if (message) {
            section.innerHTML = `<p style='font-weight:bold;'>${message}</p>` + section.innerHTML;
        }
    }
    function afficherResultats(section, data) {
        if (!data || data.length === 0) {
            section.innerHTML += '<p>Aucun résultat trouvé.</p>';
            return;
        }
        section.innerHTML += data.map(item => renderFoodItem(item)).join('');
    }
    function renderFoodItem(item) {
        let imagesHtml = '';
        if (item.has_images && item.image_urls && item.image_urls.length > 0) {
            imagesHtml = `<div class=\"gallery\">` +
                item.image_urls.map(img => `<img src=\"${img.url}\" alt=\"${item.name}\" title=\"${img.filename}\">`).join('') +
                `</div>`;
        }
        return `
            <div class=\"result-item\">
                <h3>${item.name}</h3>
                ${item.thumbnail_url ? `<img src=\"${item.thumbnail_url}\" alt=\"${item.name}\" style=\"width:120px;border-radius:8px;box-shadow:0 1px 4px #0001;\">` : ''}
                <p><strong>Catégorie :</strong> ${item.category || 'N/A'}<br>
                <strong>Région :</strong> ${item.region || 'N/A'}<br>
                <strong>Classe :</strong> ${item.ontology_class || 'N/A'}</p>
                ${imagesHtml}
            </div>
        `;
    }
}); 