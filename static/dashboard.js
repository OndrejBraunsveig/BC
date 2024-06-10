document.addEventListener('DOMContentLoaded', () => {
    // Add popup
    let addBtn = document.getElementById('add-button');
    addBtn.addEventListener('click', toggleAddMenu);

    let addCancel = document.getElementById('add-cancel-button');
    addCancel.addEventListener('click', toggleAddMenu);

    // Edit popup
    let titleCards = document.querySelectorAll('.title-card');
    titleCards.forEach(card => {
        card.addEventListener('click', setEditId);
    });

    let editCancel = document.getElementById('edit-cancel-button');
    editCancel.addEventListener('click', toggleEditMenu);

    // Delete popup
    let deleteBtns = document.querySelectorAll('.delete-button');
    deleteBtns.forEach(btn => {
        btn.addEventListener('click', setDeleteId);
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

function setEditId(e){
    let container = e.target.closest('.project-container');
    let id = container.id;
    let idField = document.getElementById('edit-id');
    idField.value = id;

    let name = container.querySelector('.project-name').innerHTML;
    let nameField = document.getElementById('edit-old-name');
    nameField.value = name;

    toggleEditMenu();
}

function toggleEditMenu(){
    let header = document.getElementById('dashboard-header');
    let main = document.getElementById('dashboard-main');
    header.classList.toggle('blur');
    main.classList.toggle('blur');
    let popup = document.getElementById('edit-popup');
    popup.classList.toggle('active');    
}

function setDeleteId(e){
    let container = e.target.closest('.project-container');
    let id = container.id;
    let idField = document.getElementById('delete-id');
    idField.value = id;
    console.log(id)

    let name = container.querySelector('.project-name').innerHTML;
    console.log(name)
    let nameField = document.getElementById('delete-old-name');
    nameField.value = name;

    toggleDangerMenu()
}

function toggleDangerMenu(){
    let header = document.getElementById('dashboard-header');
    let main = document.getElementById('dashboard-main');
    header.classList.toggle('blur');
    main.classList.toggle('blur');
    let popup = document.getElementById('danger-popup');
    popup.classList.toggle('active');    
}