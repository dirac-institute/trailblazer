function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
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
    let csrftoken = getCookie('csrftoken');
    let response = await fetch("get_images", {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'X-CSRFToken': csrftoken
        },
        body: page.toString()
    })
    let data = await response.json()
    document.getElementById("image_gallery").innerHTML = "";
    await data.data.forEach(value => {
        document.getElementById("image_gallery").innerHTML += "<div class=\"gallery_item\">\n" +
            "                <a href=\"/image?" + value.id + "\">\n" +
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