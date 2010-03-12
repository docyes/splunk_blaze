(function(){
    /** 
     * libsr4kids!
     */
    var oneshotXHR = null;
    var d = document;
    var input = document.forms[0].elements['s'];
    var cache;
    var lastHash = "";
    var oneshotQueue = false;
    var oneshotTimeout = 2000;
    var enableClearButton = {{ "true" if enable_clear_button else "false" }};
    var enableSearchLoader = {{ "true" if enable_search_loader else "false" }};
    var xsrf = xsrfExtract();
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
     * Convenience method for extracting the XSRF value used for POST, PUT or DELETE.
     * TODO: Multitype returns are bad design.
     * @return {String||undefined}
     */            
    function xsrfExtract() {
        var name = "_xsrf";
        var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
        return r ? r[1] : undefined;
    }
    /**
     * Because innerHTML is sometimes not fast enough.
     * @param {Object} target DOM element target for innerHTML replacement.
     * @param {String} innerHTML The HTML to inject.
     * @return {Object} The target DOM element. WARNING! Could be a new cloned element.
     */            
    function turboInnerHTML(target, innerHTML) {
        /*@cc_on //innerHTML is faster for IE
            target.innerHTML = innerHTML;
            return target;
        @*/
        var targetClone = target.cloneNode(false);
        targetClone.innerHTML = innerHTML;
        target.parentNode.replaceChild(targetClone, target);
        return targetClone;
    }
    /**
     * Razor thin event normalizer for adding event listeners.
     * @param {Object} obj TBD.
     * @param {String} event TBD.
     * @param {Function} callback TBD.
     */                     
    function ezEventListener(obj, event, callback, scope){
        if(window.addEventListener){
           obj.addEventListener(
                event, 
                function(evt){
                   callback(evt, evt.target);
                },
               false
           );
       }else if(window.attachEvent){
            obj.attachEvent(
                "on"+event,
                function(){
                    callback(window.event, window.event.srcElement);
                }
            );
        }
    }
    /**
     * Remove leading/trailing whitespace.
     * @param {String} str The string to perform the trim opration on.
     * @return {String} The trim formatted string.
     */
    function trimString(str){
        return (str.trim)?str.trim():str.replace(/^\s*(\S*(\s+\S+)*)\s*$/, "$1");
    }
    /**
     * Text selection abstraction. No IE support right now, sorry!
     */
    function Selection(){
        var self = this;
        self.obj;
        self.getRangeAt = function(index){
            if(self.obj.getRangeAt){
                return self.obj.getRangeAt(index);
            }else{
                return false;
            }
        }
        self.Selection = function(){
            if(window.getSelection){
                self.obj = window.getSelection();
            }else if(document.selection){
                self.obj = document.selection.createRange();
            }
        }();
    }
    /**
     * Dispatches and updates page content based on a highly tuned oneshot search. 
     * Single request channel throttled.
     */
    function oneshot(){
        if(oneshotXHR){
            oneshotQueue = true;
            return;
        }
        toggleLoader(true);
        oneshotXHR = new XMLHttpRequest();
        oneshotXHR.open("GET", "/search/new?"+oneshotInputSearch(), true);
        var xhrTimeout = setTimeout(function(){
            oneshotXHR.onreadystatechange = function(){};
            oneshotXHR.abort();
            oneshotXHR = null;
            if(oneshotQueue){
                oneshotQueue = false;
                oneshot();
            }else{
                toggleLoader(false);
            }
        }, oneshotTimeout);
        oneshotXHR.onreadystatechange = function(){
            if(oneshotXHR.readyState===4){
                clearTimeout(xhrTimeout);
                if(oneshotXHR.status==200){
                    turboInnerHTML(d.getElementById("r"), oneshotXHR.responseText);
                    setSearchHashFromInput(document.getElementById("q"));
                    var items = getEvents();
                    if(items.length>0){
                        selectEvent(items[0]);
                    }
                }else{
                    clearResultsDOM();
                }
                oneshotXHR = null;
                if(oneshotQueue){
                    oneshotQueue = false;
                    oneshot();
                }else{
                    toggleLoader(false);
                }
            }
        }
        oneshotXHR.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
        oneshotXHR.send("");//empty arg for FF <3.5
    }
    /**
     * Generates a oneshot optimized search string based on the current state of the input element. Includes intelligent cache buster.
     * @return {String} The delicious string.
     */
    function oneshotInputSearch(){
         var search = trimString(input.value);
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
     * Key code normalizer.
     * @param {Object} evt A DOM event.
     * @return {Number}
     */
    function getKeyCode(evt){
        return (evt.which)?evt.which:evt.keyCode;
    }
    /**
     * Checks if an element has a specified class or not.
     * @param {Object} el The target element.
     * @param {String} cl The class name to check against.
     * @return {Boolean}
     */
    function hasClass(el, cl) {
         return el.className.match(new RegExp('(\\s|^)'+cl+'(\\s|$)'));
    }
    /** 
     * Safely adds an additional class to an element if it does not exist already. Caution this is an element MUTATOR!
     */
    function addClass(el ,cl) {
         if(!hasClass(el, cl)) el.className += " "+ cl;
    }
    /**
     * Safely removes a class from an element.
     * @param {Object} el The target element.
     * @param {String} cl The class name to check against.
     */
    function removeClass(el, cl) {
         if(hasClass(el, cl)){
             var reg = new RegExp('(\\s|^)'+cl+'(\\s|$)');
             el.className = el.className.replace(reg,' ');
         }
    }
    /**
     * DOM preventDefault normalizer.
     *
     * @param {Object} evt The native DOM event.
     */
    function preventDefault(evt){
        if(evt.preventDefault){
            evt.preventDefault();
        }else if(evt.returnValue){
            evt.returnValue = false;
        }
    }
    /**
     * Top level event dispatcher. Centralizing DOM event observers allows for more tuning and ease of management.
     * @param {Object} evt DOM event reference.
     * @param {Object} target A normalized event target.
     */
    function dispatcher(evt, target){
         var type = evt.type;
         if(type=="mousedown" && target.id=="clear"){
             preventDefault(evt);
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
        var keyCode = getKeyCode(evt);
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
                    removeClass(terms[i], "h");
                    activeTermIndex  = i;
                    break;
                }
            }
            if(keyCode==keyCodeBindings.left){
                if(activeTermIndex>0){
                    var el = terms[activeTermIndex-1];
                    if(hasClass(el, "time")){//disable time selection
                        el = terms[((activeTermIndex-2>0)?activeTermIndex-2:terms.length-1)];
                    }
                }else{
                    var el = terms[terms.length-1];
                }
                addClass(el, "h");
                el.active = true;                                                
            }else if(keyCode==keyCodeBindings.right){
                if(activeTermIndex>-1 && activeTermIndex<terms.length-1){
                    var el = terms[activeTermIndex+1];
                }else{
                    var el = terms[0];
                    if(hasClass(el, "time")){//disable time selection
                        el = terms[1];
                    }
                }
                addClass(el, "h");
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
        var keyCode = getKeyCode(evt);
        if(keyCode==keyCodeBindings.enter){
            var str = "";
            var selectObj = new Selection();
            try{
                var str = selectObj.getRangeAt(0).toString();
            }catch(err){}
            if(str.length>0){
                input.value = input.value + freeRangeSelectFormat.replace("%s", str);
                oneshot();
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
            oneshot();
        }
        if(keyCode!=keyCodeBindings.left && keyCode!=keyCodeBindings.right && keyCode!=keyCodeBindings.up && keyCode!=keyCodeBindings.down){
            if(keyCode==keyCodeBindings.clear){
                clearAll();
            }else if(trimString(input.value).length==0){
                setHash("");
                toggleClearButton(false);
                clearResultsDOM();
            }else{
                toggleClearButton(true);
                oneshot();
            }
        }
    }
    /**
     * Clear the results DOM.
     */
    function clearResultsDOM(){
        turboInnerHTML(d.getElementById("r"), "&nbsp;");
    }
    /**
     * Clear the results DOM and the input and hide the clear button.
     */
    function clearAll(){
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
            oneshot();
            input.value = inputValue;
        }
    }
    /**
     * Shorthand for setting the window.location.hash and internal state member used for history management (back button).
     */
    function setHash(str){
         window.location.hash = str;
         lastHash = getHash();
    }
    /**
     * Accessor for safely retrieving the properly encoded location hash.
     * 
     * @return {String}
     */
    function getHash(){
        return window.location.href.split("#")[1] || "";
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
        var currentHash = getHash();
        if(currentHash!=lastHash){
            lastHash = currentHash;
            var index = currentHash.indexOf("=");
            searchValue = (index>-1)?currentHash.substring(index+1):"";
            input.value = decodeURIComponent(searchValue);
            oneshot();
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
                removeClass(terms[i], "h");
                break;
            }
        }
    }
    //if("onhashchange" in window){
    //requires logic changes.
    //    ezEventListener(window, "hashchange", hashChange);
    //}else{
        setInterval(hashChange, 400);
    //}
    ezEventListener(window, "load", hashChange);
    ezEventListener(document, "mousedown", dispatcher);
    ezEventListener(document, "keydown", dispatcher);
    ezEventListener(document, "keypress", dispatcher);
    ezEventListener(document, "keyup", dispatcher);
    ezEventListener(window, "unload", gc);
})();
