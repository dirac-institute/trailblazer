function getCookie(name) {
    //this function obtains the cookie of the website.
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        let cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            let cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}


async function get_images(page) {
    //This function sends and receives data asyncronosly to the server.
    let csrftoken = getCookie('csrftoken');//obtains the token required to send and receive
    let response = await fetch("", {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'X-CSRFToken': csrftoken
        },
        body: page.toString()
    });//this is the request to the server
    let data = await response.json()//get the json
    //Now the code bellow edits the main website changing the images
    document.getElementById("image_gallery").innerHTML = "";
    await data.data.forEach(value => {
        document.getElementById("image_gallery").innerHTML += "<div class=\"gallery_item\">\n" +
            "                <a href=\"/gallery/image?" + value.id + "\">\n" +
            "                    <img src=\"/media/" + value.name + "\" width=\"300\" alt=”C:\\Users\\thisi\\PycharmProjects\\trailblazer\\trail\\media\\frame-g-002728-2-0424.png”\n" +
            "                         id=”showSimilarInPopup”>\n" +
            "                    <div class=”caption”>\n" +
            "                        <span class=\"date\">" + value.date + "</span>\n" +
            "                        <span>" + value.caption + "</span>\n" +
            "                    </div>\n" +
            "                </a>\n" +
            "            </div>"
    })
    for (let i = 0; i < document.getElementsByClassName("pagenum").length; i++) {
        document.getElementsByClassName("pagenum")[i].classList.remove("active")
    }
    document.getElementById("pagenum_" + page).classList.add("active")
}