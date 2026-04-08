// =====================================================
// BayBay - Application JavaScript
// =====================================================

// Modal functions
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('hidden');
        modal.style.display = 'flex';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('hidden');
        modal.style.display = 'none';
    }
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

    notification.className = `fixed top-4 right-4 z-[100] ${colors[type] || colors['info']} text-white px-5 py-3 rounded-xl shadow-lg flex items-center gap-3 transform transition-all duration-300 translate-x-full`;

    notification.innerHTML = `
        <div class="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center">
            <i class="fas ${icons[type] || icons['info']} text-sm"></i>
        </div>
        <span class="font-medium">${message}</span>
    `;

    document.body.appendChild(notification);

    // Animate in
    setTimeout(() => {
        notification.classList.remove('translate-x-full');
    }, 10);

    // Auto remove after 3 seconds
    setTimeout(() => {
        notification.classList.add('translate-x-full');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Bien modal
function openBienModal(sciId) {
    const title = document.getElementById('bienModalTitle');
    const form = document.getElementById('bienForm');
    const editId = document.getElementById('bienEditId');
    const sciIdField = document.getElementById('bienSciId');

    if (title) title.innerHTML = '<i class="fas fa-home text-green-500 mr-2"></i>Nouveau Bien';
    if (form) form.reset();
    if (editId) editId.value = '';
    if (sciIdField) sciIdField.value = sciId;

    openModal('bienModal');
}

// Appartement modal
function openAppartModal(bienId) {
    const title = document.getElementById('appartModalTitle');
    const form = document.getElementById('appartForm');
    const editId = document.getElementById('appartEditId');
    const bienIdField = document.getElementById('appartBienId');

    if (title) title.innerHTML = '<i class="fas fa-door-open text-purple-500 mr-2"></i>Nouvel Appartement';
    if (form) form.reset();
    if (editId) editId.value = '';
    if (bienIdField) bienIdField.value = bienId;

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
            setTimeout(() => window.location.reload(), 500);
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
                modal.classList.add('hidden');
                modal.style.display = 'none';
            }
        });
    });

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
        showNotification(sciId ? 'SCI modifiée' : 'SCI créée', 'success');
        setTimeout(() => window.location.reload(), 500);
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

    const url = bienId ? `/api/bien/${bienId}` : '/api/bien';
    const method = bienId ? 'PUT' : 'POST';

    const response = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (response.ok) {
        showNotification(bienId ? 'Bien modifié' : 'Bien créé', 'success');
        setTimeout(() => window.location.reload(), 500);
    } else {
        showNotification('Erreur', 'error');
    }
});

document.getElementById('appartForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());
    const appartId = data.appart_id;
    delete data.appart_id;

    const url = appartId ? `/api/appartement/${appartId}` : '/api/appartement';
    const method = appartId ? 'PUT' : 'POST';

    const response = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (response.ok) {
        showNotification(appartId ? 'Appartement modifié' : 'Appartement créé', 'success');
        setTimeout(() => window.location.reload(), 500);
    } else {
        showNotification('Erreur', 'error');
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
        showNotification(locataireId ? 'Locataire modifié' : 'Locataire créé', 'success');
        setTimeout(() => window.location.reload(), 500);
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
        showNotification('Paiement enregistré', 'success');
        setTimeout(() => window.location.reload(), 500);
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
        showNotification('Appel de loyer créé', 'success');
        setTimeout(() => window.location.reload(), 500);
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
        setTimeout(() => window.location.reload(), 500);
    } else {
        showNotification('Erreur', 'error');
    }
});

document.getElementById('scheduleForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());

    const checkboxes = document.querySelectorAll('input[name="locataires_ids"]:checked');
    data.locataires_ids = Array.from(checkboxes).map(cb => cb.value);
    data.tous_locataires = data.destinataires === 'tous';
    data.recurrent = document.getElementById('scheduleRecurrent')?.checked || false;

    const response = await fetch('/api/programmation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (response.ok) {
        closeModal('scheduleModal');
        showNotification('Programmation créée', 'success');
        setTimeout(() => window.location.reload(), 500);
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
