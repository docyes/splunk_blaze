(function(){
    /** 
     * libsr4kids!
     */
    var oneshotXHR = new blaze.base.xhr.SingleChannel();
    var d = document;
    var input = document.forms[0].elements['s'];
    var cache;
    var lastHash = "";
    var oneshotQueue = false;
    var oneshotTimeout = 2000;
    var enableClearButton = {{ "true" if enable_clear_button else "false" }};
    var enableSearchLoader = {{ "true" if enable_search_loader else "false" }};
    var xsrf = blaze.base.xsrfExtract();
    var keyCodeBindings = {
        "left":37,
        "right":39,
        "up":38,
        "down":40,
        "enter":13,
        "clear":27
    };
    var termSelectFormat = ' "%s"';
    var freeRangeSelectFormat = ' "*%s*"';
    /**
     * Artificial XHR life.
     */            
    if(typeof(XMLHttpRequest)==="undefined"){
        XMLHttpRequest = function() {
            try{return new ActiveXObject("Msxml2.XMLHTTP.6.0");}catch(e){}
            try{return new ActiveXObject("Msxml2.XMLHTTP.3.0");}catch(e){}
            try{return new ActiveXObject("Msxml2.XMLHTTP");}catch(e){}
            try{return new ActiveXObject("Microsoft.XMLHTTP");}catch(e){}
            throw new Error("This browser does not support XMLHttpRequest.");
        };
    }
    document.body.className = document.body.className + " " + ((navigator.userAgent.indexOf("AppleWebKit")!=-1)?"webkit":"");
    updateCache();
    setInterval(updateCache, {{ search_browser_cache_ttl }});
    input.focus();
    /**
     * Updates the cache member value used in managing expiry of every search get request.
     */
    function updateCache(){
        cache = cache = (new Date()).getTime().toString(36);
    }
    /**
     * Convenience wrapper for executing a search request.
     */
    function oneshotRequest(){
        oneshotXHR.request("GET", "{{ reverse_url("search") }}?"+oneshotInputSearch(), oneshotHandler, oneshotTimeout);
    }
    /**
     * Event handler for xhr search.
     * @param {Object} event blaze.base.xhr.SingleChannel event object.
     */
    function oneshotHandler(event){
        switch(event.type){
            case "abort":
                oneshotQueue = false;
                toggleLoader(false);
                break;
            case "block":
                oneshotQueue = true;
                break
            case "request":
                toggleLoader(true);
                break;
            case "timeout":
                oneshotRequest();
                break;
            case "response":
                toggleLoader(false);
                if(event.status==200){
                    blaze.base.turboInnerHTML(d.getElementById("r"), event.responseText);
                    setSearchHashFromInput(document.getElementById("q"));
                    var items = getEvents();
                    if(items.length>0){
                        selectEvent(items[0]);
                    }
                }else{
                    clearResultsDOM();
                }
                if(oneshotQueue){
                    oneshotQueue = false;
                    oneshotRequest();
                }
                break;
            default:
                break;
        }
    }
    /**
     * Generates a oneshot optimized search string based on the current state of the input element. Includes intelligent cache buster.
     * @return {String} The delicious string.
     */
    function oneshotInputSearch(){
         var search = blaze.base.trimString(input.value);
         var sid = document.getElementById("sid");
         var sidParam = "";
         if(sid){
             sidParam = "&sid="+encodeURIComponent(sid.value);
         }
         if(search.length==0){
             search = " ";
         }
         return "search="+encodeURIComponent(search)+"&c="+encodeURIComponent(cache)+sidParam;
    }
    /**
     * Top level event dispatcher. Centralizing DOM event observers allows for more tuning and ease of management.
     * @param {Object} evt DOM event reference.
     * @param {Object} target A normalized event target.
     */
    function dispatcher(evt, target){
         var type = evt.type;
         if(type=="mousedown" && target.id=="clear"){
             blaze.base.preventDefault(evt);
             clearAll();
             input.focus();
         }else if(type=="keydown" && (navigator.appVersion && navigator.appVersion.indexOf("Safari")!=-1) || type=="keypress" && !(navigator.appVersion && navigator.appVersion.indexOf("Safari")!=-1)){
             keyboardNavigate(evt, target);
         }else if(type=="keyup"){
             keyboardOneshot(evt, target);
         }
    }
    /**
     * Enables the ability to navigate the document using keyboard bindings.
     * TODO: Push more event related switching to dispatcher.
     * @param {Object} evt DOM event reference.
     * @param {Object} target A normalized event target.             
     */
    function keyboardNavigate(evt, target){
        var keyCode = blaze.base.getKeyCode(evt);
        if(keyCode==keyCodeBindings.up || keyCode==keyCodeBindings.down){
            var items = getEvents();
            if(items.length==0){
                return;
            }
            var activeIndex = -1;
            for(var i=0; i<items.length; i++){
                if(items[i].active){
                    items[i].active = false;
                    items[i].style.background = "";
                    activeIndex  = i;
                    break;
                }
            }
            if(activeIndex>-1){
                resetTerms(items[activeIndex]);
            }
            if(keyCode==keyCodeBindings.up){
                if(activeIndex>0){
                    var el = items[activeIndex-1];
                }else{
                    var el = items[items.length-1];
                }
                selectEvent(el);
            }else if(keyCode==keyCodeBindings.down){
                if(activeIndex>-1 && activeIndex<items.length-1){
                    var el = items[activeIndex+1];
                }else{
                    var el = items[0];
                }
                selectEvent(el);
            }
        }
        if(keyCode==keyCodeBindings.left || keyCode==keyCodeBindings.right){
            var items = getEvents();
            if(items.length==0){
                return;
            }
            var activeIndex = -1;
            for(var i=0; i<items.length; i++){
                if(items[i].active){
                    activeIndex  = i;
                    break;
                }
            }
            if(activeIndex==-1){
                return;
            }
            var terms = getTerms(items[activeIndex]);
            var activeTermIndex = -1;
            for(var i=0; i<terms.length; i++){
                if(terms[i].active){
                    terms[i].active = false;
                    blaze.base.removeClass(terms[i], "h");
                    activeTermIndex  = i;
                    break;
                }
            }
            if(keyCode==keyCodeBindings.left){
                if(activeTermIndex>0){
                    var el = terms[activeTermIndex-1];
                    if(blaze.base.hasClass(el, "time")){//disable time selection
                        el = terms[((activeTermIndex-2>0)?activeTermIndex-2:terms.length-1)];
                    }
                }else{
                    var el = terms[terms.length-1];
                }
                blaze.base.addClass(el, "h");
                el.active = true;                                                
            }else if(keyCode==keyCodeBindings.right){
                if(activeTermIndex>-1 && activeTermIndex<terms.length-1){
                    var el = terms[activeTermIndex+1];
                }else{
                    var el = terms[0];
                    if(blaze.base.hasClass(el, "time")){//disable time selection
                        el = terms[1];
                    }
                }
                blaze.base.addClass(el, "h");
                el.active = true;
            }
        }
    }
    /**
     * Keyboard oneshot search handing.
     * TODO: Push more event related switching to dispatcher.
     * @param {Object} evt DOM event reference.
     * @param {Object} target A normalized event target.             
     */ 
    function keyboardOneshot(evt, target){
        var keyCode = blaze.base.getKeyCode(evt);
        if(keyCode==keyCodeBindings.enter){
            var str = "";
            var selectObj = new blaze.base.Selection();
            try{
                var str = selectObj.getRangeAt(0).toString();
            }catch(err){}
            if(str.length>0){
                input.value = input.value + freeRangeSelectFormat.replace("%s", str);
                oneshotRequest();
                return;
            }
            var items = getEvents();
            var activeIndex = -1;
            for(var i=0; i<items.length; i++){
                if(items[i].active){
                    activeIndex  = i;
                    break;
                }
            }
            if(activeIndex==-1){
                return;
            }
            var terms = getTerms(items[activeIndex]);
            var activeTermIndex = -1;
            for(var i=0; i<terms.length; i++){
                if(terms[i].active){
                    activeTermIndex  = i;
                    break;
                }
            }
            if(activeTermIndex==-1){
                return;
            }
            var str = (terms[activeTermIndex].textContent)?terms[activeTermIndex].textContent:terms[activeTermIndex].innerText;
            input.value = input.value + termSelectFormat.replace("%s", str);
            oneshotRequest();
        }
        if(keyCode!=keyCodeBindings.left && keyCode!=keyCodeBindings.right && keyCode!=keyCodeBindings.up && keyCode!=keyCodeBindings.down){
            if(keyCode==keyCodeBindings.clear){
                clearAll();
            }else if(blaze.base.trimString(input.value).length==0){
                oneshotXHR.abort();
                setHash("");
                toggleClearButton(false);
                clearResultsDOM();
            }else{
                toggleClearButton(true);
                oneshotRequest();
            }
        }
    }
    /**
     * Clear the results DOM.
     */
    function clearResultsDOM(){
        blaze.base.turboInnerHTML(d.getElementById("r"), "&nbsp;");
    }
    /**
     * Clear the results DOM and the input and hide the clear button.
     */
    function clearAll(){
         oneshotXHR.abort();
         input.value = "";
         setHash("");
         clearResultsDOM();
         toggleClearButton(false);
    }
    /**
     * Control the display of the clear button.
     *
     * @param {Boolean} display Flag to control if the button is shown or not.
     */
    function toggleClearButton(display){
         if(enableClearButton){
             document.getElementById("clear").style.display = (display)?"block":"none";
         }
    }
    /**
     * Control the display of the loader icon. Works around limitations of some browsers (FF)
     * that reset animated gif state by using -left position.
     * 
     * @param {Boolean) display Control the display state of the animated loader.
     */
    function toggleLoader(display){
        if(enableSearchLoader){
            document.getElementById("loader").style.left = (display)?"110px":"-1000px";
        }
    }
    /**
     * General garbage collection routine, pick up your trash!
     */
    function gc(){
        if(document.getElementById("sid")){
            var inputValue = input.value;
            input.value = "|";
            oneshotRequest();
            input.value = inputValue;
        }
    }
    /**
     * Shorthand for setting the window.location.hash and internal state member used for history management (back button).
     */
    function setHash(str){
         window.location.hash = str;
         lastHash = blaze.base.getHash();
    }
    /**
     * Convenience method for setting the search hash from a DOM element object.
     * 
     * @param {Object} obj DOM element reference to object with a value attribute.
     */            
    function setSearchHashFromInput(obj){
        if(obj && obj.value){
            setHash("q=" + obj.value);
        }
    }
    //TODO: Clean me....
    function hashChange(){
        var currentHash = blaze.base.getHash();
        if(currentHash!=lastHash){
            lastHash = currentHash;
            var index = currentHash.indexOf("=");
            searchValue = (index>-1)?currentHash.substring(index+1):"";
            input.value = decodeURIComponent(searchValue);
            oneshotRequest();
        }
    }
    function selectEvent(el){
        el.active = true;
        el.style.background = "url({{ static_url("img/arrow.png") }}) no-repeat 0px 7px";
    }
    function getEvents(){
        return d.getElementById("r").getElementsByTagName("li");
    }
    function getTerms(parent){
        return parent.getElementsByTagName("em");
    }
    function resetTerms(parent){
        var terms = getTerms(parent);
        for(var i=0; i<terms.length; i++){
            if(terms[i].active){
                terms[i].active = false;
                blaze.base.removeClass(terms[i], "h");
                break;
            }
        }
    }
    //if("onhashchange" in window){
    //requires logic changes.
    //    blaze.base.ezEventListener(window, "hashchange", hashChange);
    //}else{
        setInterval(hashChange, 400);
    //}
    hashChange();
    blaze.base.ezEventListener(document, "mousedown", dispatcher);
    blaze.base.ezEventListener(document, "keydown", dispatcher);
    blaze.base.ezEventListener(document, "keypress", dispatcher);
    blaze.base.ezEventListener(document, "keyup", dispatcher);
    blaze.base.ezEventListener(window, "unload", gc);
})();
