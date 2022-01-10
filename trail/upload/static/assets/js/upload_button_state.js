/**
 * Changes the button state when the copyright disclaimer is checked.
 */
$(document).ready(function($) {
    var copyrightBox = document.getElementById('copyright-disclaimer');
    var uploadButton = document.querySelector("button");
    copyrightBox.addEventListener('change', () => {
        if (copyrightBox.checked){
            if (uploadButton.classList.contains("disabled")){
                uploadButton.classList.remove("disabled");
            }
        }
        else{
            if (!uploadButton.classList.contains("disabled")){
                uploadButton.classList.add("disabled");
            }
        }
    });
});

