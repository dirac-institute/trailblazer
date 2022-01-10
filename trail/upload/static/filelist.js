'use strict';

// adapted from github.com/morlandi/django-upload-form


/**
   UploadFormFileList is a mutable container meant to contain the list of
   files selected for uploadm it also refreshes the UI, to display added or
   removed files.
 */
window.UploadFormFileList = (function() {

    /** List of actively selected files **/
    var fileList = [];
    /** The page element wrapping the area where files are displayed **/
    var wrapper = null;

    /**
     * Assigns the wrapper element and clears it, initializes an empty file list.
     * @param  {Object}  wrapper_element  The page element wrapping the list display.
     */
    function initialize(wrapper_element) {
        wrapper = $(wrapper_element);
        wrapper.find('.uploadform_remove_all_files').on('click', clear);
        fileList = [];
    }

    /**
     * Get the list of selected files.
     * @return {Array} fileList List of selected files.
     */
    function get_filelist() {
        return fileList;
    }

    /**
     * Removes specified item from file list array.
     * @param  {Object}   filename  Name of the file to remove.
     * @return {Boolean}  success   True if successful, false otherwise.
     */
    function removeByFilename(filename) {
        var rc = false;
        $(fileList).each(function(index, item) {
            if (item.name == filename) {
                fileList.splice(index, 1);  // remove
                //console.log('"%o" removed', filename);
                rc = true;
                return false;  // break
            }
        });
        return rc;
    }

    /**
     * Add a file to file list being careful not to insert duplicates.
     * @param  {Object}  file  File to insert.
     */
    function add(file) {
        removeByFilename(file.name);
        fileList.push(file);
    }

    /**
     * Deletes a table row and the file associated to this row then refreshes
     * the UI. (Action bound to the delete button in the upload form file list.)
     * @param  {Object}  element  Table element to remove.
     */
    function deleteFileListRow(element) {
        event.preventDefault();
        var row = $(event.target).closest('tr');
        var filename = row.find('.filename').text();
        removeByFilename(filename);
        refreshUI();
    }

    /**
     * Removes all files in the file list and then refreshes the UI.
     * @param  {Object}  event  Event that triggers the clear.
     *
     * Note: the default event behavior will be suppressed.
     */
    function clear(event) {
        // Remove all files in fileList array,
        // then refresh UI
        if (event) {
            event.preventDefault();
        }
        fileList = [];
        refreshUI();
    }

    /**
     * Converts the given file size (in unknown units) into human readable size.
     * @param  {Number}  b   Integer file size, usually in bytes.
     * @return {Number}  fs  Float file size, in human readable format.
     */
    function _fileSize(b) {
        var u = 0;
        var s = 1024;
        while (b >= s || -b >= s) {
            b /= s;
            u++;
        }
        return (u ? b.toFixed(1) + ' ' : b) + ' KMGTPEZY'[u] + 'B';
    }

    /**
     * Refreshes the UI, displaying the table of selected files. When there are
     * no selected files the table is hidden.
     */
    function refreshUI() {
        if (fileList.length <= 0) {
            wrapper.hide();
            wrapper.find('.uploadform_remove_file').off();
        }
        else {
            wrapper.show();
            var fileDisplay = wrapper.find('table tbody');

            fileDisplay.html('');
            $(fileList).each(function(index, file) {
                var fname = file.name;
                var ftype = file.name.split('.').pop();
                var fsize = _fileSize(file.size);
                var rmlink = '<a href="#" class="uploadform_remove_file" title="Remove item"><img src="/static/icons/trash-svgrepo-com.svg" class="icon"></a>';
                fileDisplay.append(
                    '<tr>' +
                    '<td class="filetype">' + ftype + '</td>' +
                    '<td class="filename">' + fname + '</td>' +
                    '<td class="numeric">' + fsize + '</td>' +
                    '<td class="delete">' + rmlink + '</td>' +
                    '</tr>'
                );
            });
            wrapper.find('.uploadform_remove_file').off().on('click', deleteFileListRow);
        }
    }

    return {
        initialize: initialize,
        get_filelist: get_filelist,
        add: add,
        refreshUI: refreshUI
    };

})();
