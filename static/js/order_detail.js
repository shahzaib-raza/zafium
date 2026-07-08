document.addEventListener("DOMContentLoaded",function(){

/* ==========================
    PROGRESS
========================== */

const progress=document.querySelector(".progress-fill");

if(progress){

    const value=progress.dataset.progress;

    progress.style.width="0";

    requestAnimationFrame(()=>{

        progress.style.width=value+"%";

    });

}


/* ==========================
    LIVE STAR RATING
========================== */

const stars=document.querySelectorAll(".rating-selector input");

stars.forEach(star=>{

    star.addEventListener("change",function(){

        const value=parseInt(this.value);

        stars.forEach(s=>{

            const icon=s.nextElementSibling;

            if(parseInt(s.value)<=value){

                icon.style.color="#fbbf24";

            }

            else{

                icon.style.color="#9ca3af";

            }

        });

    });

});


/* ==========================
    AJAX REVIEW
========================== */

const form=document.getElementById("reviewForm");

if(form){

form.addEventListener("submit",function(e){

e.preventDefault();

const submitBtn=form.querySelector("button");

submitBtn.disabled=true;

submitBtn.innerText="Submitting...";

fetch(form.action,{

method:"POST",

body:new FormData(form),

headers:{

"X-Requested-With":"XMLHttpRequest"

}

})

.then(res=>res.json())

.then(data=>{

submitBtn.disabled=false;

submitBtn.innerText="Submit Review";

if(data.success){

showToast("Review submitted successfully.");

form.reset();

}

else{

showToast(data.message || "Unable to submit review.");

}

})

.catch(()=>{

submitBtn.disabled=false;

submitBtn.innerText="Submit Review";

showToast("Something went wrong.");

});

});

}



/* ==========================
    TOAST
========================== */

function showToast(message){

const toast=document.createElement("div");

toast.className="dashboard-toast";

toast.innerHTML=message;

document.body.appendChild(toast);

setTimeout(()=>{

toast.classList.add("show");

},50);

setTimeout(()=>{

toast.classList.remove("show");

setTimeout(()=>toast.remove(),300);

},2500);

}

});