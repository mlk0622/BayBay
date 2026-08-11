// =====================================================
// BayBay - Application JavaScript
// =====================================================

// Modal functions
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    // Full-page overlay setup
    modal.style.position = 'fixed';
    modal.style.top = '0';
    modal.style.left = '0';
    modal.style.right = '0';
    modal.style.bottom = '0';
    modal.style.width = '100vw';
    modal.style.height = '100vh';
    modal.style.zIndex = '99999';
    modal.style.display = 'flex';
    modal.style.alignItems = 'center';
    modal.style.justifyContent = 'center';
    modal.style.padding = '1.5rem';
    modal.style.boxSizing = 'border-box';
    // Frosted glass full-page blur
    if (!modal.style.background || modal.style.background === 'none') {
        modal.style.background = 'rgba(0,0,0,0.65)';
    }
    modal.style.backdropFilter = 'blur(10px)';
    modal.style.webkitBackdropFilter = 'blur(10px)';

    // Center the inner content
    const inner = modal.firstElementChild;
    if (inner) {
        inner.style.margin = 'auto';
        inner.style.maxHeight = '85vh';
        inner.style.overflowY = 'auto';
        inner.style.position = 'relative';
        inner.style.zIndex = '100000';
    }

    modal.classList.remove('hidden');
    modal.classList.add('active-modal');
    document.body.style.overflow = 'hidden';

    // Close when clicking the backdrop
    modal._backdropHandler = function(e) {
        if (e.target === modal) closeModal(modalId);
    };
    modal.addEventListener('click', modal._backdropHandler);
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    modal.classList.remove('active-modal');
    if (modal._backdropHandler) {
        modal.removeEventListener('click', modal._backdropHandler);
        delete modal._backdropHandler;
    }
    setTimeout(() => {
        if (!modal.classList.contains('active-modal')) {
            modal.style.display = 'none';
            modal.classList.add('hidden');
        }
    }, 200);
    // Restore body scroll only if no other modal is open
    const anyOpen = document.querySelector('[id$="Modal"].active-modal, [id$="modal"].active-modal');
    if (!anyOpen) document.body.style.overflow = '';
}

function closeEmailPreviewModal() {
    closeModal('emailPreviewModal');
}

function openEmailPreviewModal(title, subject, bodyHtml) {
    const modalTitle = document.getElementById('emailPreviewTitle');
    const modalSubject = document.getElementById('emailPreviewSubject');
    const previewFrame = document.getElementById('emailPreviewFrame');

    if (modalTitle) modalTitle.textContent = title || 'Aperçu du mail';
    if (modalSubject) modalSubject.textContent = subject || '';
    if (previewFrame) previewFrame.srcdoc = bodyHtml || '<html><body style="font-family:Arial,sans-serif;padding:24px;">Aucun contenu à afficher.</body></html>';

    openModal('emailPreviewModal');
}

// Fonction pour ouvrir le modal d'édition de SCI
async function openEditSciModal(sciId) {
    try {
        const response = await fetch(`/api/sci/${sciId}`);
        if (!response.ok) throw new Error('Erreur lors du chargement');

        const sci = await response.json();

        // Remplir le formulaire
        document.getElementById('sciId').value = sci.id;
        document.getElementById('sciNom').value = sci.nom || '';
        document.getElementById('sciAdresse').value = sci.adresse || '';
        document.getElementById('sciCodePostal').value = sci.code_postal || '';
        document.getElementById('sciVille').value = sci.ville || '';
        document.getElementById('sciSiret').value = sci.siret || '';
        document.getElementById('sciEmail').value = sci.email || '';
        document.getElementById('sciType').value = sci.type_sci || 'Immeuble';

        // Changer le titre et le bouton
        document.getElementById('sciModalTitle').innerHTML = '<i class="fas fa-building text-primary mr-2"></i>Modifier la SCI';
        document.getElementById('sciSubmitBtn').innerHTML = '<i class="fas fa-check mr-2"></i>Enregistrer les modifications';

        openModal('sciModal');
    } catch (error) {
        showNotification('Erreur lors du chargement de la SCI', 'error');
    }
}

// Notification system
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existing = document.getElementById('notification');
    if (existing) existing.remove();

    const notification = document.createElement('div');
    notification.id = 'notification';

    const colors = {
        'success': 'bg-green-500',
        'error': 'bg-red-500',
        'warning': 'bg-orange-500',
        'info': 'bg-blue-500'
    };

    const icons = {
        'success': 'fa-check',
        'error': 'fa-times',
        'warning': 'fa-exclamation',
        'info': 'fa-info'
    };

    notification.className = `fixed top-4 right-4 z-[100] ${colors[type] || colors['info']} text-white px-5 py-3 rounded-xl shadow-lg flex items-center gap-3 transition-opacity duration-300 opacity-0`;

    notification.innerHTML = `
        <div class="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center">
            <i class="fas ${icons[type] || icons['info']} text-sm"></i>
        </div>
        <span class="font-medium">${message}</span>
    `;

    document.body.appendChild(notification);

    // Animate in
    setTimeout(() => {
        notification.classList.remove('opacity-0');
        notification.classList.add('opacity-100');
    }, 10);

    // Auto remove after 3 seconds
    setTimeout(() => {
        notification.classList.remove('opacity-100');
        notification.classList.add('opacity-0');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Bien modal
function resetBienTypeOptions() {
    const typeSelect = document.getElementById('bienType');
    if (!typeSelect) return;
    Array.from(typeSelect.options).forEach((opt) => {
        opt.disabled = false;
    });
}

async function openBienModal(sciId) {
    const title = document.getElementById('bienModalTitle');
    const form = document.getElementById('bienForm');
    const editId = document.getElementById('bienEditId');
    const sciIdField = document.getElementById('bienSciId');

    if (title) title.innerHTML = '<i class="fas fa-home text-green-500 mr-2"></i>Nouveau Bien';
    if (form) form.reset();
    if (editId) editId.value = '';
    if (sciIdField) sciIdField.value = sciId || '';
    resetBienTypeOptions();
    setBienCharges([]);
    if (sciId) {
        await syncBienTypeWithSci(sciId);
    } else {
        const typeSelect = document.getElementById('bienType');
        if (typeSelect) typeSelect.value = 'Immeuble';
    }

    openModal('bienModal');
}

function openSciChoiceModal() {
    openModal('choixSciModal');
}

function selectSciForNewBien(sciId) {
    closeModal('choixSciModal');
    openBienModal(sciId);
}

// Appartement modal
function openAppartModal(bienId) {
    const title = document.getElementById('appartModalTitle');
    const form = document.getElementById('appartForm');
    const editId = document.getElementById('appartEditId');
    const bienIdField = document.getElementById('appartBienId');

    if (title) title.innerHTML = '<i class="fas fa-door-open text-purple-500 mr-2"></i>Nouveau Lot';
    if (form) form.reset();
    if (editId) editId.value = '';
    if (bienIdField) bienIdField.value = bienId;
    setAppartCharges([]);
    toggleAppartFields();

    openModal('appartModal');
}

// Delete modal
function showDeleteModal(type, id, name) {
    const typeField = document.getElementById('deleteType');
    const idField = document.getElementById('deleteId');
    const message = document.getElementById('deleteMessage');

    if (typeField) typeField.value = type;
    if (idField) idField.value = id;
    if (message) message.textContent = `Êtes-vous sûr de vouloir supprimer "${name}" ?`;

    openModal('deleteModal');
}

async function confirmDelete() {
    const type = document.getElementById('deleteType')?.value;
    const id = document.getElementById('deleteId')?.value;

    const endpoints = {
        'sci': `/api/sci/${id}`,
        'bien': `/api/bien/${id}`,
        'appartement': `/api/appartement/${id}`,
        'locataire': `/api/locataire/${id}`,
        'appel': `/api/appel-loyer/${id}`,
        'quittance': `/api/quittance/${id}`,
        'programmation': `/api/programmation/${id}`,
        'paiement': `/api/paiement/${id}`
    };

    try {
        const response = await fetch(endpoints[type], { method: 'DELETE' });
        if (response.ok) {
            closeModal('deleteModal');
            showNotification('Supprimé avec succès', 'success');
            setTimeout(() => { if (window.refreshPage) window.refreshPage(); else window.location.reload(); }, 500);
        } else {
            showNotification('Erreur lors de la suppression', 'error');
        }
    } catch (err) {
        showNotification('Erreur lors de la suppression', 'error');
    }
}

// Close modal when clicking outside
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('[class*="modal"], [id*="Modal"]').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal(modal.id);
            }
        });
    });

    const sciType = document.getElementById('sciType');
    if (sciType && !sciType.value) {
        sciType.value = 'Immeuble';
    }

    const addChargeBtn = document.getElementById('addBienChargeBtn');
    if (addChargeBtn) {
        addChargeBtn.addEventListener('click', () => {
            const container = document.getElementById('bienChargesContainer');
            if (!container) return;
            container.appendChild(renderBienChargeRow());
        });
    }
    setBienCharges([]);

    const addAppartChargeBtn = document.getElementById('addAppartChargeBtn');
    if (addAppartChargeBtn) {
        addAppartChargeBtn.addEventListener('click', () => {
            const container = document.getElementById('appartChargesContainer');
            if (!container) return;
            container.appendChild(renderAppartChargeRow());
        });
    }
    setAppartCharges([]);

    const appartType = document.getElementById('appartType');
    if (appartType) {
        appartType.addEventListener('change', toggleAppartFields);
        toggleAppartFields();
    }

    // Schedule destinataires change
    const scheduleDestinataires = document.getElementById('scheduleDestinataires');
    if (scheduleDestinataires) {
        scheduleDestinataires.addEventListener('change', function() {
            const div = document.getElementById('locatairesSelectionDiv');
            if (div) {
                if (this.value === 'selection') {
                    div.classList.remove('hidden');
                } else {
                    div.classList.add('hidden');
                }
            }
        });
    }
});

// Form submissions
document.getElementById('sciForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());
    const sciId = data.sci_id;
    delete data.sci_id;

    const url = sciId ? `/api/sci/${sciId}` : '/api/sci';
    const method = sciId ? 'PUT' : 'POST';

    const response = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (response.ok) {
        const payload = await response.json().catch(() => ({}));
        const newSciId = payload.id;

        closeModal('sciModal');
        if (!sciId && newSciId) {
            showNotification('SCI créée. Ajoutez maintenant un bien dans cette SCI.', 'success');
            setTimeout(() => openBienModal(newSciId), 250);
            return;
        }

        showNotification(sciId ? 'SCI modifiée' : 'SCI créée', 'success');
        setTimeout(() => { if (window.refreshPage) window.refreshPage(); else window.location.reload(); }, 500);
    } else {
        showNotification('Erreur', 'error');
    }
});

document.getElementById('bienForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());
    const bienId = data.bien_id;
    delete data.bien_id;

    data.charges = collectBienCharges();

    const url = bienId ? `/api/bien/${bienId}` : '/api/bien';
    const method = bienId ? 'PUT' : 'POST';

    const response = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (response.ok) {
        closeModal('bienModal');
        showNotification(bienId ? 'Bien modifié' : 'Bien créé', 'success');
        setTimeout(() => { if (window.refreshPage) window.refreshPage(); else window.location.reload(); }, 500);
    } else {
        const payload = await response.json().catch(() => ({}));
        showNotification(payload.error || 'Erreur', 'error');
    }
});

document.getElementById('appartForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());
    const appartId = data.appart_id;
    delete data.appart_id;

    const type = data.type_appartement;

    if (type !== 'Appartement') {
        data.etage = '';
        data.numero_porte = '';
    }
    if (type !== 'Box') {
        data.numero_box = '';
    }
    if (type !== 'Local Commerciale') {
        data.nom_entreprise = '';
    }

    if (type === 'Appartement' || type === 'Local Commerciale') {
        data.charges_json = collectAppartCharges();
    } else {
        data.charges_json = [];
    }

    const url = appartId ? `/api/appartement/${appartId}` : '/api/appartement';
    const method = appartId ? 'PUT' : 'POST';

    const response = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (response.ok) {
        closeModal('appartementModal');
        showNotification(appartId ? 'Lot modifié' : 'Lot créé', 'success');
        setTimeout(() => { if (window.refreshPage) window.refreshPage(); else window.location.reload(); }, 500);
    } else {
        const payload = await response.json().catch(() => ({}));
        showNotification(payload.error || 'Erreur', 'error');
    }
});

document.getElementById('locataireForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());
    const locataireId = data.locataire_id;
    delete data.locataire_id;

    if (!data.appartement_id) data.appartement_id = null;

    const url = locataireId ? `/api/locataire/${locataireId}` : '/api/locataire';
    const method = locataireId ? 'PUT' : 'POST';

    const response = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (response.ok) {
        closeModal('locataireModal');
        showNotification(locataireId ? 'Locataire modifié' : 'Locataire créé', 'success');
        setTimeout(() => { if (window.refreshPage) window.refreshPage(); else window.location.reload(); }, 500);
    } else {
        showNotification('Erreur', 'error');
    }
});

document.getElementById('paiementForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());

    const response = await fetch('/api/paiement', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (response.ok) {
        closeModal('paiementModal');
        showNotification('Paiement enregistré', 'success');
        setTimeout(() => { if (window.refreshPage) window.refreshPage(); else window.location.reload(); }, 500);
    } else {
        showNotification('Erreur', 'error');
    }
});

document.getElementById('appelLoyerForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());

    const response = await fetch('/api/appel-loyer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (response.ok) {
        closeModal('appelLoyerModal');
        showNotification('Appel de loyer créé', 'success');
        setTimeout(() => { if (window.refreshPage) window.refreshPage(); else window.location.reload(); }, 500);
    } else {
        showNotification('Erreur', 'error');
    }
});

document.getElementById('quittanceForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());

    const response = await fetch('/api/quittance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (response.ok) {
        showNotification('Quittance créée', 'success');
        setTimeout(() => { if (window.refreshPage) window.refreshPage(); else window.location.reload(); }, 500);
    } else {
        showNotification('Erreur', 'error');
    }
});


// Fonction pour ouvrir le modal de paiement (utilisée depuis comptes_locatifs.html)
function openPaiementModal(locataireId) {
    const locataireIdField = document.getElementById('paiementLocataireId');
    const moisField = document.getElementById('paiementMois');
    const anneeField = document.getElementById('paiementAnnee');
    const dateField = document.getElementById('paiementDate');

    if (!locataireIdField || !moisField || !anneeField || !dateField) {
        console.error('Éléments du modal paiement non trouvés');
        showNotification('Erreur: modal de paiement non disponible', 'error');
        return;
    }

    locataireIdField.value = locataireId;
    const today = new Date();
    moisField.value = today.getMonth() + 1;
    anneeField.value = today.getFullYear();
    dateField.value = today.toISOString().split('T')[0];
    openModal('paiementModal');
}

// Charges functions
function renderBienChargeRow(charge = { libelle: '', montant: '' }) {
    const row = document.createElement('div');
    row.className = 'grid grid-cols-[1fr_140px_auto] gap-2 items-center';
    row.innerHTML = `
        <input type="text" class="bien-charge-libelle w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="Libelle" value="${charge.libelle || ''}">
        <input type="number" min="0" step="0.01" class="bien-charge-montant w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="0.00" value="${charge.montant || ''}">
        <button type="button" class="bien-charge-remove w-9 h-9 rounded-lg bg-red-50 text-red-500 hover:bg-red-100"><i class="fas fa-trash"></i></button>
    `;
    row.querySelector('.bien-charge-remove')?.addEventListener('click', () => row.remove());
    return row;
}

function setBienCharges(charges = []) {
    const container = document.getElementById('bienChargesContainer');
    if (!container) return;
    container.innerHTML = '';
    (charges || []).forEach((charge) => container.appendChild(renderBienChargeRow(charge)));
    if (!container.children.length) {
        container.appendChild(renderBienChargeRow());
    }
}

function collectBienCharges() {
    const rows = document.querySelectorAll('#bienChargesContainer > div');
    const charges = [];
    rows.forEach((row) => {
        const libelle = row.querySelector('.bien-charge-libelle')?.value?.trim();
        const montant = row.querySelector('.bien-charge-montant')?.value;
        if (libelle) {
            charges.push({ libelle, montant: montant || 0 });
        }
    });
    return charges;
}

async function syncBienTypeWithSci(sciId) {
    const typeSelect = document.getElementById('bienType');
    if (!typeSelect || !sciId) return;

    try {
        const response = await fetch(`/api/sci/${sciId}`);
        if (!response.ok) return;
        const sci = await response.json();
        const isEntrepotSci = (sci.type_sci || '') === 'Entrepot';

        Array.from(typeSelect.options).forEach((opt) => {
            opt.disabled = isEntrepotSci && opt.value !== 'Entrepot';
        });

        if (isEntrepotSci) {
            typeSelect.value = 'Entrepot';
        }
    } catch (_) {
        // Ne bloque pas l'ouverture du modal si le chargement echoue.
    }
}

function renderAppartChargeRow(charge = { libelle: '', montant: '' }) {
    const row = document.createElement('div');
    row.className = 'grid grid-cols-[1fr_140px_auto] gap-2 items-center';
    row.innerHTML = `
        <input type="text" class="appart-charge-libelle w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="Libellé" value="${charge.libelle || ''}">
        <input type="number" min="0" step="0.01" class="appart-charge-montant w-full px-3 py-2 border border-slate-300 rounded-lg" placeholder="0.00" value="${charge.montant || ''}">
        <button type="button" class="appart-charge-remove w-9 h-9 rounded-lg bg-red-50 text-red-500 hover:bg-red-100"><i class="fas fa-trash"></i></button>
    `;
    row.querySelector('.appart-charge-remove')?.addEventListener('click', () => row.remove());
    return row;
}

function setAppartCharges(charges = []) {
    const container = document.getElementById('appartChargesContainer');
    if (!container) return;
    container.innerHTML = '';
    (charges || []).forEach((charge) => container.appendChild(renderAppartChargeRow(charge)));
    if (!container.children.length) {
        container.appendChild(renderAppartChargeRow());
    }
}

function collectAppartCharges() {
    const rows = document.querySelectorAll('#appartChargesContainer > div');
    const charges = [];
    rows.forEach((row) => {
        const libelle = row.querySelector('.appart-charge-libelle')?.value?.trim();
        const montant = row.querySelector('.appart-charge-montant')?.value;
        if (libelle) {
            charges.push({ libelle, montant: montant || 0 });
        }
    });
    return charges;
}

function toggleAppartFields() {
    const type = document.getElementById('appartType')?.value;
    const porteGroup = document.getElementById('appartNumeroPorteGroup');
    const boxGroup = document.getElementById('appartNumeroBoxGroup');
    const nomEntrepriseGroup = document.getElementById('appartNomEntrepriseGroup');
    const chargesGroup = document.getElementById('appartChargesGroup');
    const porteInput = document.getElementById('appartNumero');
    const etageInput = document.getElementById('appartEtage');
    const boxInput = document.getElementById('appartNumeroBox');

    // Masquer tous les groupes
    [porteGroup, boxGroup, nomEntrepriseGroup, chargesGroup].forEach(g => g?.classList.add('hidden'));
    if (porteInput) porteInput.required = false;
    if (boxInput) boxInput.required = false;

    if (!type) return;

    if (type === 'Appartement') {
        porteGroup?.classList.remove('hidden');
        chargesGroup?.classList.remove('hidden');
        if (porteInput) porteInput.required = true;
        if (etageInput) etageInput.value = etageInput.value || '';
    } else if (type === 'Box') {
        boxGroup?.classList.remove('hidden');
        if (boxInput) boxInput.required = true;
        if (etageInput) etageInput.value = '';
        if (porteInput) porteInput.value = '';
    } else if (type === 'Local Commerciale') {
        nomEntrepriseGroup?.classList.remove('hidden');
        chargesGroup?.classList.remove('hidden');
    } else {
        // Entrepôt
        if (porteInput) porteInput.value = '';
        if (etageInput) etageInput.value = '';
        if (boxInput) boxInput.value = '';
    }
}

//# sourceMappingURL=app.js.map
