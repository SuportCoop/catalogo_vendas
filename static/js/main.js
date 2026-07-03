document.addEventListener("DOMContentLoaded", function() {
    
    // ==========================================
    // FECHAMENTO DE ALERTAS DE SUCESSO/ERRO
    // ==========================================
    const alertCloses = document.querySelectorAll(".alert-close");
    alertCloses.forEach(btn => {
        btn.addEventListener("click", function() {
            const alert = this.closest(".alert");
            alert.style.opacity = "0";
            setTimeout(() => {
                alert.remove();
            }, 300);
        });
    });

    // Auto dispensar alertas depois de 4 segundos
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = "0";
            setTimeout(() => {
                alert.remove();
            }, 300);
        }, 4000);
    });

    // ==========================================
    // MODAL DE DETALHES DO PRODUTO (DINÂMICO)
    // ==========================================
    const modalOverlay = document.getElementById("productModal");
    const openButtons = document.querySelectorAll(".open-detail-modal");
    
    if (modalOverlay && openButtons.length > 0) {
        const closeModalBtn = modalOverlay.querySelector(".close-modal");
        
        // Elementos do Modal
        const modalTitle = modalOverlay.querySelector("#modalProductTitle");
        const modalCode = modalOverlay.querySelector("#modalProductCode");
        const modalCategory = modalOverlay.querySelector("#modalProductCategory");
        const modalPrice = modalOverlay.querySelector("#modalProductPrice");
        const modalStock = modalOverlay.querySelector("#modalProductStock");
        const modalDesc = modalOverlay.querySelector("#modalProductDesc");
        const mainImg = modalOverlay.querySelector("#modalMainImg");
        const thumbnailsContainer = modalOverlay.querySelector("#modalThumbnails");
        const addToCartBtn = modalOverlay.querySelector("#modalAddToCartBtn");
        
        openButtons.forEach(button => {
            button.addEventListener("click", function(e) {
                e.preventDefault();
                const productId = this.getAttribute("data-id");
                
                // Mostrar estado de "Carregando"
                modalTitle.textContent = "Carregando...";
                modalCode.textContent = "";
                modalCategory.textContent = "";
                modalPrice.textContent = "R$ 0,00";
                modalStock.textContent = "-";
                modalDesc.textContent = "Buscando informações do produto...";
                mainImg.src = "";
                thumbnailsContainer.innerHTML = "";
                addToCartBtn.href = "#";
                addToCartBtn.style.display = "none";
                
                // Abrir o modal overlay
                modalOverlay.classList.add("active");
                
                // Buscar dados do produto via API
                fetch(`/produto/${productId}/`)
                    .then(response => response.json())
                    .then(data => {
                        // Preencher informações básicas
                        modalTitle.textContent = data.name;
                        modalCode.textContent = `Código: ${data.code}`;
                        modalCategory.textContent = data.category;
                        modalPrice.textContent = `R$ ${data.sale_price.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                        
                        if (data.stock > 0) {
                            modalStock.innerHTML = `<span style="color: var(--success);">Em estoque (${data.stock})</span>`;
                            addToCartBtn.style.display = "block";
                            addToCartBtn.href = `/carrinho/adicionar/${data.id}/`;
                        } else {
                            modalStock.innerHTML = `<span style="color: var(--danger);">Indisponível</span>`;
                            addToCartBtn.style.display = "none";
                        }
                        
                        modalDesc.textContent = data.description || "Nenhuma descrição fornecida.";
                        
                        // Configurar galeria de fotos
                        if (data.images && data.images.length > 0) {
                            mainImg.src = data.images[0];
                            
                            // Se houver mais de uma imagem, criar miniaturas
                            if (data.images.length > 1) {
                                data.images.forEach((imgUrl, index) => {
                                    const thumb = document.createElement("img");
                                    thumb.src = imgUrl;
                                    thumb.className = "thumbnail-img" + (index === 0 ? " active" : "");
                                    thumb.alt = `Miniatura ${index + 1}`;
                                    
                                    // Ação de trocar imagem principal
                                    thumb.addEventListener("click", function() {
                                        mainImg.src = imgUrl;
                                        modalOverlay.querySelectorAll(".thumbnail-img").forEach(t => t.classList.remove("active"));
                                        this.classList.add("active");
                                    });
                                    
                                    thumbnailsContainer.appendChild(thumb);
                                });
                            }
                        } else {
                            // Fallback caso não existam imagens
                            mainImg.src = "/static/images/placeholder.png";
                        }
                    })
                    .catch(err => {
                        console.error("Erro ao buscar detalhes do produto:", err);
                        modalTitle.textContent = "Erro ao carregar";
                        modalDesc.textContent = "Não foi possível carregar as informações deste produto.";
                    });
            });
        });
        
        // Fechar Modal
        closeModalBtn.addEventListener("click", function() {
            modalOverlay.classList.remove("active");
        });
        
        modalOverlay.addEventListener("click", function(e) {
            if (e.target === modalOverlay) {
                modalOverlay.classList.remove("active");
            }
        });
        
        document.addEventListener("keydown", function(e) {
            if (e.key === "Escape" && modalOverlay.classList.contains("active")) {
                modalOverlay.classList.remove("active");
            }
        });
    }

    // ==========================================
    // MENU TOGGLE (MOBILE NAVIGATION)
    // ==========================================
    const menuToggle = document.getElementById("menuToggle");
    const navLinks = document.querySelector(".nav-links");
    
    if (menuToggle && navLinks) {
        menuToggle.addEventListener("click", function(e) {
            e.stopPropagation();
            navLinks.classList.toggle("active");
            
            // Alterar ícone do toggle (bars <=> xmark)
            const icon = menuToggle.querySelector("i");
            if (navLinks.classList.contains("active")) {
                icon.className = "fa-solid fa-xmark";
            } else {
                icon.className = "fa-solid fa-bars";
            }
        });
        
        // Fechar o menu ao clicar fora dele
        document.addEventListener("click", function(e) {
            if (!navLinks.contains(e.target) && !menuToggle.contains(e.target)) {
                navLinks.classList.remove("active");
                const icon = menuToggle.querySelector("i");
                if (icon) {
                    icon.className = "fa-solid fa-bars";
                }
            }
        });
    }
});
