document.addEventListener('DOMContentLoaded', () => {
    // Add popup
    let addBtn = document.getElementById('add-button');
    addBtn.addEventListener('click', toggleAddMenu);

    let addCancel = document.getElementById('add-cancel-button');
    addCancel.addEventListener('click', toggleAddMenu);

    // Edit popup
    let titleCards = document.querySelectorAll('.title-card');
    titleCards.forEach(card => {
        card.addEventListener('click', toggleEditMenu);
    });

    let editCancel = document.getElementById('edit-cancel-button');
    editCancel.addEventListener('click', toggleEditMenu);

    // Delete popup
    let deleteBtns = document.querySelectorAll('.delete-button');
    deleteBtns.forEach(btn => {
        btn.addEventListener('click', toggleDangerMenu);
    });

    let deleteCancel = document.getElementById('delete-cancel-button');
    deleteCancel.addEventListener('click', toggleDangerMenu);
});

function toggleAddMenu(){
    let header = document.getElementById('dashboard-header');
    let main = document.getElementById('dashboard-main');
    header.classList.toggle('blur');
    main.classList.toggle('blur');
    let popup = document.getElementById('add-popup');
    popup.classList.toggle('active');
}

function toggleEditMenu(){
    let header = document.getElementById('dashboard-header');
    let main = document.getElementById('dashboard-main');
    header.classList.toggle('blur');
    main.classList.toggle('blur');
    let popup = document.getElementById('edit-popup');
    popup.classList.toggle('active');    
}

function toggleDangerMenu(){
    let header = document.getElementById('dashboard-header');
    let main = document.getElementById('dashboard-main');
    header.classList.toggle('blur');
    main.classList.toggle('blur');
    let popup = document.getElementById('danger-popup');
    popup.classList.toggle('active');    
}