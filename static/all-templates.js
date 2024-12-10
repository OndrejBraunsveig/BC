let templateFile;
let pointsFile;

document.addEventListener('DOMContentLoaded', () => {

    // Add
    let addBtn = document.getElementById('add-button');
    addBtn.addEventListener('click', toggleAddMenu);

    let addCancel = document.getElementById('add-cancel-button');
    addCancel.addEventListener('click', toggleAddMenu);

    let stlFileLabel = document.getElementById('stl-file-label');
    let stlFileInput = document.getElementById('stl-file-input');
    stlFileInput.addEventListener('input', (e) => {
        stlFileLabel.innerHTML = e.target.files[0].name;
    });

    let csvFileLabel = document.getElementById('csv-file-label');
    let csvFileInput = document.getElementById('csv-file-input');
    csvFileInput.addEventListener('input', (e) => {
        csvFileLabel.innerHTML = e.target.files[0].name;
    });

    // Edit
    let editIdField = document.getElementById('edit-id');
    let editNameField = document.getElementById('edit-old-name');
    let templateNames = document.querySelectorAll('.template-name');
    templateNames.forEach(name => {
        name.addEventListener('click', (e) => {
            let tableRow = e.target.closest('tr');
            let templateId = tableRow.id;
            editIdField.value = templateId;

            let templateName = name.innerHTML;
            editNameField.value = templateName;
            toggleEditMenu()
        });
    });

    let editCancel = document.getElementById('edit-cancel-button');
    editCancel.addEventListener('click', toggleEditMenu);

    // Delete
    let deleteIdField = document.getElementById('delete-id');
    let deleteNameField = document.getElementById('delete-old-name');
    let deleteBtns = document.querySelectorAll('.delete-svg');
    deleteBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            let tableRow = e.target.closest('tr');
            let templateId = tableRow.id;
            deleteIdField.value = templateId;

            let templateName = tableRow.querySelector('.template-name').innerHTML;
            deleteNameField.value = templateName;
            toggleDeleteMenu()
        });
    });

    let deleteCancel = document.getElementById('delete-cancel-button');
    deleteCancel.addEventListener('click', toggleDeleteMenu);
});

function toggleBlur(){
    let header = document.getElementById('dashboard-header');
    let table = document.getElementById('template-table');
    header.classList.toggle('blur');
    table.classList.toggle('blur');
}

function toggleAddMenu(){
    toggleBlur();
    let popup = document.getElementById('add-popup');
    popup.classList.toggle('active');
}

function toggleEditMenu(){
    toggleBlur();
    let popup = document.getElementById('edit-popup');
    popup.classList.toggle('active');
}

function toggleDeleteMenu(){
    toggleBlur();
    let popup = document.getElementById('danger-popup');
    popup.classList.toggle('active');
}