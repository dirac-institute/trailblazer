document.getElementById("querybtn").addEventListener("click", refresh)

function refresh() {
    placeholder = document.getElementById("tablecontent")

    fetch('/app/observation/', {
      method: "GET",
      credentials: "same-origin",
      headers: {
        Accept: "application/text",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCookie("csrftoken"),
      },
    })
      .then((res) => res.text())
      .then((data) => {
          placeholder.innerHTML = data
      })
      .catch((err) => {
        console.log("err in fetch", err);
      });
}