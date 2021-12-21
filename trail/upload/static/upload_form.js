'use strict';

// adapted from github.com/morlandi/django-upload-form

$(document).ready(function($) {
    UploadForm.initialize($('.uploadform_drop_area'));
});

/**
   * UploadForm contains the following client side functionality for the upload
   * app:
   *     - updating the dynamic list of selected files (UploadFormFileList) on
   *       drop events
   *     - displaying and updating progress bar on submit events
   *     - sending the AJAX POST upload request on submit event.
   *
   * Note that while UploadForm is responsible for updating the file list, the
   * UI refresh displaying these files is the prerogative of UploadFormFileList.
 */
window.UploadForm = (function() {

    /**
     * Bind highlighting to dragover and dragleave events and bind onFormSubmit
     * function to the submit element action.
     * @param  {Object} dropArea The page element containing our form (Note:
     *                           the form is expected to contain sub-elements
     *                           f.e. file_list_wrapper, used here)
     */
    function initialize(dropArea) {
        //UploadFormFileList.initialize('.uploadform_drop_area .file_list_wrapper');
        //var dropArea = $('.uploadform_drop_area');
        UploadFormFileList.initialize(dropArea.find('.file_list_wrapper'));
        dropArea.on('dragenter dragover', function(event) {
            event.preventDefault();
            dropArea.addClass('highlight');
        });
        dropArea.on('dragleave', function(event) {
            event.preventDefault();
            dropArea.removeClass('highlight');
        });
        dropArea.on('drop', onDropAreaDrop);
        dropArea.find('form').on('submit', onFormSubmit);
    }

    /**
     * On drag and drop event remove the element highlight and handle dropped
     * files.
     * @param  {Event} event Drop event.
     */
    function onDropAreaDrop(event) {

        event.preventDefault();
        var target = $(event.target);
        var dropArea = target.closest('.uploadform_drop_area');

        dropArea.removeClass('highlight');
        //var files = event.dataTransfer.files;
        //event.originalEvent.dataTransfer.dropEffect = 'copy';
        var files = event.originalEvent.dataTransfer.files;
        dropArea.find('form input[type="file"]').prop('files', files);
        handleFiles(files);
    }

    /**
     * Validates file. Additional validation will be performed server-side.
     * File is consider valid when it's of a type image, or plain text, or
     * contains the string `fit` or `fits` in its extensions when the file
     * type is unknown.
     *
     * @param  {FileList} files   files to be added to the UI.
     * @return {Object}   result  result of validation. The boolean attribute
     *                            `valid`, which is true when file is valid and
     *                            false otherwise. For an non-valid file,
     *                            attribute `reason` explains why.
     */
    function validate_file(file) {
        var message = "Reason unknown";

        // when we encounter any of the fits.fz.bz2.whatever extensions
        // this whole function is a mess but will have to do for now
        var typeok=false;
        if (file.type == ""){
            $(file.name.split('.')).each(function(index, ext){
                if (ext == "fits" || ext == "fit"){
                    typeok = true;
                }
            });
        } else if (file.type =="image/fits" || file.type == "text/plain"){
            typeok = true;
        } else{
            typeok = false;
            message = "File type not allowed.";
        }

        var sizeok=false;
        if (MAX_FILE_SIZE_MB > 0){
            if (file.size < MAX_FILE_SIZE_MB*1000*1000){
                var sizeok = true;
            } else{
                sizeok = false;
                message = "File size exceeds " + MAX_FILE_SIZE_MB + "MB.";
            }
        } else{
            sizeok = true;
        }

        var acceptable = typeok & sizeok;
        return {valid: acceptable, reason: message};
    }

    /**
     * Given a list of files adds them to the UploadFormFileList and refreshes
     * it (displaying the new files). Performs basic file type and filesize
     * validation.
     *
     * @param  {FileList} files files to be added to the UI.
     */
    function handleFiles(files) {
        // Append new files to fileList and perform basic validation
        var failed_validation = [];
        $(files).each(function(index, file) {
            var validation = validate_file(file);
            if (validation.valid){
                UploadFormFileList.add(file);
            }
            else{
                failed_validation.push([file, validation.reason]);
            }
        });

        var alertwrap = $(".alert");
        var alertlist = alertwrap.find(".errorlist");
        alertlist.html("");
        alertwrap.hide();
        if (failed_validation.length > 0){
            alertwrap.show();
            $(failed_validation).each(function(index, item){
                alertlist.append(
                    '<li>' + item[0].name +': ' + item[1] + '</li>'
                );
            });
        }

        // Update UI
        UploadFormFileList.refreshUI();
    }

    /**
     * Attempts to retrieve the session cookie.
     * Note: returns undefined when no cookies match the name.
     * @param  {String}             name    Name of the cookie.
     * @return {String, undefined}  cookie  Cookie value or undefined.
     */
    function getCookie(name) {
        var value = '; ' + document.cookie;
        var parts = value.split('; ' + name + '=');
        if (parts.length == 2) return parts.pop().split(';').shift();
    };

    /**
     * On submit event, fetches a list of selected files, reveals the progress
     * bar and sends the data.
     * @param  {Event}  event  Submit event.
     */
    function onFormSubmit(event)
    {
        event.preventDefault();

        var target = $(event.target);
        var dropArea = target.closest('.uploadform_drop_area');
        var form = $(dropArea.find('form'));

        dropArea.find('.progress').show();
        var progressBar = dropArea.find('.progress-bar');
        var url = form.attr('action');

        var filelist = UploadFormFileList.get_filelist();

        var data = new FormData();

        var inputs = form.serializeArray();
        $.each(inputs, function (i, input) {
            data.append(input.name, input.value);
        });

        $(filelist).each(function(index, file) {
            data.append('files', file);
        });

        // Make an AJAX POST request and wait for it's completion. If success
        //
        var promise = sendFormData(data, url, progressBar);
        promise
            .done(function(data) {
                onSendFormDataDone(dropArea, data);
            })
            .fail(onSendFormDataFail);
    }

    /**
     * Creates an POST request that sends data to the server, updating the
     * progress bar along the way.
     * @param  {Array}   data        Data to upload.
     * @param  {String}  url         Action target url (f.e. "/upload/success")
     * @param  {Object}  progressBar Page element containing the progress bar.
     * @return {Object}  promise     Upload promise.

     */
    function sendFormData(data, url, progressBar) {
        var promise = $.ajax({
            type: "POST",
            url: url,
            data: data,
            dataType: 'json',
            processData: false,
            contentType: false,
            headers: {"X-CSRFToken": getCookie('csrftoken')},
            xhr: function() {
                var xhr = $.ajaxSettings.xhr();
                xhr.upload.onprogress = function(e) {
                    var progress = Math.floor(e.loaded / e.total *100)
                    var progressPct = progress + '%';
                    if (progress > 99){
                        var notifyUser = $(".uploadform_user_message");
                        notifyUser.show();
                    }
                    if (progressBar !== null) {
                        progressBar.css('width', progressPct);
                        progressBar.text(progress);
                    }
                };
              return xhr;
            }
        });
        return promise;
    }

    /**
     * Handles a successful post-upload page actions.
     * @param  {Object}         dropArea  page element (div) containing drop area
     * @param  {Object, Array}  data      response (JsonResponse) or array
     *                                    containing the response as first element
     *                                    and data. The response is expected to
     *                                    contain an action (`replace` or
     *                                    `redirect`). On replace, the entire
     *                                    upload form area is re-initialized.
     */
    function onSendFormDataDone(dropArea, data) {
        var response = data;
        if (Array.isArray(data)) {
            response = data[0];
        }
        switch (response.action) {
            case 'replace':
                dropArea.replaceWith(response.html);
                initialize($('.uploadform_drop_area'));
                break;
            case 'redirect':
                window.location.replace(response.url);
                break;
        }
    }

    /**
     * Handles a failed post-upload page actions.
     * @param  {Object}  jqXHR       The XHR request that failed.
     * @param  {String}  textStatus  Ignored.
     */
    function onSendFormDataFail(jqXHR, textStatus) {
        console.log('ERROR: %o', jqXHR);
        alert('ERROR: ' + jqXHR.statusText);
        window.location.replace(url);
    }

    return {
        initialize: initialize,
        handleFiles: handleFiles
    };

})();
