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
    });
    //replace table content
    document.getElementById("table_content").innerHTML = await response.text()
}