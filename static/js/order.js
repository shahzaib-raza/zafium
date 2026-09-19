const currency = window.ORDER_CONFIG.currency;
const usdToPkrRate = Number(window.ORDER_CONFIG.usdToPkrRate);

const subcategories = window.ORDER_CONFIG.subcategories;
const categories = window.ORDER_CONFIG.categories;
const selectedServices = window.ORDER_CONFIG.selectedServices;


function formatPrice(usdAmount) {

    if (currency === "PKR") {

        const pkrAmount =
            usdAmount * usdToPkrRate;

        return `₨${Math.round(pkrAmount).toLocaleString()}`;
    }

    return `$${usdAmount.toFixed(2)}`;
}


function populateSubcategories(
    item,
    categoryId
) {

    const subSelect =
        item.querySelector(".subcategory");


    const filtered =
        Object.entries(subcategories)
            .filter(
                ([id, service]) =>
                    service.category == categoryId
            );


    subSelect.innerHTML = `
        <option value="">
            Select Service
        </option>

        ${
            filtered.map(
                ([id, service]) =>
                    `<option value="${id}">
                        ${service.name}
                        (${formatPrice(service.price)})
                    </option>`
            ).join("")
        }
    `;
}


function createItem(
    selectedSubcategoryId = null
) {

    const div =
        document.createElement("div");


    div.classList.add(
        "order-item",
        "card"
    );


    div.innerHTML = `
        <select class="category">

            <option value="">
                Select Category
            </option>

            ${Object.entries(categories).map(
                ([id, category]) =>
                    `<option value="${id}">
                        ${category.name}
                    </option>`
            ).join("")}

        </select>


        <select class="subcategory">

            <option value="">
                Select Service
            </option>

        </select>


        <input
            type="number"
            class="qty"
            value="1"
            min="1"
        >


        <span class="price">
            ${formatPrice(0)}
        </span>


        <span
            class="remove-btn"
            style="cursor:pointer; margin-left:10px;"
        >
            ✕
        </span>
    `;


    document
        .getElementById("order-items")
        .appendChild(div);


    attachEvents(div);


    /*
     * If a solution supplied a service,
     * automatically select it.
     */

    if (selectedSubcategoryId) {

        const service =
            subcategories[selectedSubcategoryId];


        if (!service) {
            return;
        }


        const categorySelect =
            div.querySelector(".category");

        const subcategorySelect =
            div.querySelector(".subcategory");


        categorySelect.value =
            service.category;


        populateSubcategories(
            div,
            service.category
        );


        subcategorySelect.value =
            selectedSubcategoryId;


        update(div);
    }
}


function collectItems() {

    const items = [];


    document
        .querySelectorAll(".order-item")
        .forEach(item => {

            const subId =
                item.querySelector(
                    ".subcategory"
                ).value;


            const qty =
                item.querySelector(
                    ".qty"
                ).value;


            if (!subId) {
                return;
            }


            items.push(
                `${subId}|${qty}`
            );
        });


    document.getElementById(
        "items-input"
    ).value =
        JSON.stringify(items);
}


function attachEvents(item) {

    const catSelect =
        item.querySelector(".category");

    const subSelect =
        item.querySelector(".subcategory");

    const qtyInput =
        item.querySelector(".qty");

    const removeBtn =
        item.querySelector(".remove-btn");


    catSelect.addEventListener(
        "change",
        () => {

            const catId =
                catSelect.value;


            populateSubcategories(
                item,
                catId
            );


            update(item);
        }
    );


    subSelect.addEventListener(
        "change",
        () => update(item)
    );


    qtyInput.addEventListener(
        "input",
        () => update(item)
    );


    removeBtn.addEventListener(
        "click",
        () => {

            item.remove();

            updateTotal();
        }
    );
}


function update(item) {

    const subId =
        item.querySelector(
            ".subcategory"
        ).value;


    const qty =
        parseInt(
            item.querySelector(
                ".qty"
            ).value || 0
        );


    if (!subId) {
        return;
    }


    const price =
        subcategories[subId].price *
        qty;


    item.querySelector(
        ".price"
    ).innerText =
        formatPrice(price);


    updateTotal();
}


function updateTotal() {

    let total = 0;


    const summary =
        document.getElementById(
            "summary-items"
        );


    summary.innerHTML = "";


    document
        .querySelectorAll(".order-item")
        .forEach(item => {

            const subId =
                item.querySelector(
                    ".subcategory"
                ).value;


            const qty =
                parseInt(
                    item.querySelector(
                        ".qty"
                    ).value || 0
                );


            if (!subId) {
                return;
            }


            const price =
                subcategories[subId].price *
                qty;


            total += price;


            const row =
                document.createElement("div");


            row.classList.add(
                "summary-row"
            );


            row.innerHTML = `
                <span>
                    ${subcategories[subId].name}
                    × ${qty}
                </span>

                <span>
                    ${formatPrice(price)}
                </span>
            `;


            summary.appendChild(row);
        });


    document.getElementById(
        "total"
    ).innerText =
        formatPrice(total);
}


/*
 * INITIALIZATION
 */

document
    .getElementById("add-item")
    .addEventListener(
        "click",
        () => createItem()
    );


/*
 * If a solution/package was selected,
 * create only its predefined services.
 *
 * Otherwise create one empty service row.
 */

if (
    selectedServices &&
    selectedServices.length > 0
) {

    selectedServices.forEach(
        serviceId => {

            createItem(
                Number(serviceId)
            );
        }
    );

} else {

    createItem();
}


/*
 * ORDER FORM
 */

const orderForm =
    document.getElementById(
        "order-form"
    );


orderForm.addEventListener(
    "submit",
    function () {

        collectItems();
    }
);


/*
 * ATTACHMENTS
 */

const attachmentInput =
    document.getElementById(
        "attachments"
    );


const attachmentList =
    document.getElementById(
        "attachment-list"
    );


const attachmentSize =
    document.getElementById(
        "attachment-size"
    );


const MAX_TOTAL_SIZE =
    25 * 1024 * 1024; // 25 MB


function validateAttachments() {

    let totalSize = 0;


    attachmentList.innerHTML = "";


    for (
        const file of attachmentInput.files
    ) {

        totalSize += file.size;


        const item =
            document.createElement(
                "div"
            );


        item.textContent =
            `${file.name} — ` +
            `${(
                file.size /
                1024 /
                1024
            ).toFixed(2)} MB`;


        attachmentList.appendChild(
            item
        );
    }


    const totalMB =
        totalSize /
        (1024 * 1024);


    attachmentSize.textContent =
        `${totalMB.toFixed(2)} MB / 25 MB`;


    if (
        totalSize >
        MAX_TOTAL_SIZE
    ) {

        attachmentSize.style.color =
            "red";


        attachmentInput.setCustomValidity(
            "The total size of all attachments cannot exceed 25 MB."
        );


        return false;

    } else {

        attachmentSize.style.color =
            "";


        attachmentInput.setCustomValidity(
            ""
        );


        return true;
    }
}


attachmentInput.addEventListener(
    "change",
    function () {

        validateAttachments();
    }
);


orderForm.addEventListener(
    "submit",
    function (event) {

        if (!validateAttachments()) {

            event.preventDefault();

            attachmentInput.reportValidity();
        }
    }
);