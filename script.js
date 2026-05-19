// Инициализация библиотеки анимаций при прокрутке (AOS)
AOS.init({
    duration: 1000,
    once: false
});

// Эффект Sticky Navbar (затемнение меню при прокрутке вниз)
window.addEventListener('scroll', () => {
    const nav = document.getElementById('navbar');
    window.scrollY > 50 ? nav.classList.add('scrolled') : nav.classList.remove('scrolled');
});

// Данные факультетов для модальных окон
const facultyData = {
    'kiber': {
        icon: '⚙️',
        title: 'Kiberfiziki ulgamlar',
        desc: 'Bu fakultetde talyplar robototehnika, mehatronika we senagat awtomatizasiýasy barada çuňňur bilim alýarlar. Dünýäniň öňdebaryjy tehnologiýalaryny ulanyp, akylly enjamlary döretmegi öwrenýärler.',
        specs: ['Robototehnika we mehatronika', 'Senagat awtomatizasiýasy', 'Mikroelektronika we sxematehnika']
    },
    'komp': {
        icon: '💻',
        title: 'Kompýuter ylymlary',
        desc: 'IT pudagynyň ýüregi. Bu ýerde siz diňe bir kod ýazmagy däl, eýsem emeli intellekt ulgamlaryny we kiberhowpsuzlyk binýatlaryny gurmagy öwrenersiňiz.',
        specs: ['Emeli intellekt (AI) we Maşyn öwrenmesi', 'Maglumat we kiberhowpsuzlyk', 'Ulgamlaýyn programmirleme']
    },
    'nano': {
        icon: '🔬',
        title: 'Nanotehnologiýalar',
        desc: 'Gelejegiň materiallary we innowasion himiýa. Talyplar laboratoriýalarda täze nesil energiýa çeşmeleri we nanomateriallar bilen tanyşýarlar.',
        specs: ['Himiýa tehnologiýalary', 'Fizika we materialşynaslyk', 'Biotehnologiýa esaslary']
    }
};

// Функция открытия модального окна
function openModal(id) {
    const data = facultyData[id];

    // Заполняем попап данными выбранного факультета
    document.getElementById('modalIcon').innerText = data.icon;
    document.getElementById('modalTitle').innerText = data.title;
    document.getElementById('modalDesc').innerText = data.desc;

    // Генерируем список направлений
    let specsHtml = '';
    data.specs.forEach(spec => {
        specsHtml += `<li><span>✔</span> ${spec}</li>`;
    });
    document.getElementById('modalSpecs').innerHTML = specsHtml;

    // Показываем окно и блокируем прокрутку страницы
    document.getElementById('facultyModal').classList.add('show');
    document.body.style.overflow = 'hidden';
}

// Функция закрытия модального окна
function closeModal() {
    document.getElementById('facultyModal').classList.remove('show');
    document.body.style.overflow = 'auto'; // Возвращаем прокрутку страницы
}

// Закрытие окна при клике на темный фон вне попапа
window.onclick = function (event) {
    const modal = document.getElementById('facultyModal');
    if (event.target == modal) {
        closeModal();
    }
}

// Обработка отправки формы связи через Backend
async function submitForm(event) {
    event.preventDefault(); // Останавливаем перезагрузку страницы

    // Собираем данные из полей
    const name = document.getElementById('userName').value;
    const email = document.getElementById('userEmail').value;
    const message = document.getElementById('userMessage').value;

    try {
        // Отправляем POST-запрос на наш Python-сервер
        const response = await fetch('http://127.0.0.1:8000/api/contact', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name: name, email: email, message: message })
        });

        const result = await response.json();

        // Проверяем, успешно ли сервер принял данные
        if (result.status === "success") {
            alert('Üstünlikli ugradyldy! Biziň bilen habarlaşanyňyz üçin sag boluň.');
            event.target.reset(); // Очищаем поля формы
        } else {
            alert('Ýalňyşlyk ýüze çykdy. Täzeden synanyşyň.');
        }

    } catch (error) {
        console.error("Бэкенд не отвечает:", error);
        alert('Serwer bilen aragatnaşyk ýok. Python бэкенд запущен?');
    }
}