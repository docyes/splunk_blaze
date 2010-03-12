blaze = window.blaze || {};
blaze.base = {
    /**
     * DOM preventDefault normalizer.
     *
     * @param {Object} evt The native DOM event.
     */
    preventDefault: function(evt){
        if(evt.preventDefault){
            evt.preventDefault();
        }else if(evt.returnValue){
            evt.returnValue = false;
        }
    },
    /**
     * Checks if an element has a specified class or not.
     * @param {Object} el The target element.
     * @param {String} cl The class name to check against.
     * @return {Boolean}
     */
    hasClass: function(el, cl) {
         return el.className.match(new RegExp('(\\s|^)'+cl+'(\\s|$)'));
    },
    /** 
     * Safely adds an additional class to an element if it does not exist already. Caution this is an element MUTATOR!
     */
    addClass: function(el ,cl) {
         if(!hasClass(el, cl)) el.className += " "+ cl;
    },
    /**
     * Safely removes a class from an element.
     * @param {Object} el The target element.
     * @param {String} cl The class name to check against.
     */
    removeClass: function(el, cl) {
         if(hasClass(el, cl)){
             var reg = new RegExp('(\\s|^)'+cl+'(\\s|$)');
             el.className = el.className.replace(reg,' ');
         }
    },
    /**
     * Key code normalizer.
     * @param {Object} evt A DOM event.
     * @return {Number}
     */
    getKeyCode: function(evt){
        return (evt.which)?evt.which:evt.keyCode;
    },
    /**
     * Accessor for safely retrieving the properly encoded location hash.
     * 
     * @return {String}
     */
    getHash: function(){
        return window.location.href.split("#")[1] || "";
    },
    /**
     * Razor thin event normalizer for adding event listeners.
     * @param {Object} obj TBD.
     * @param {String} event TBD.
     * @param {Function} callback TBD.
     */                     
    ezEventListener: function(obj, event, callback, scope){
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
    },
    /**
     * Text selection class abstraction. No IE support right now, sorry!
     */
    Selection: function(){
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
    },
    /**
     * Remove leading/trailing whitespace.
     * @param {String} str The string to perform the trim opration on.
     * @return {String} The trim formatted string.
     */
    trimString: function(str){
        return (str.trim)?str.trim():str.replace(/^\s*(\S*(\s+\S+)*)\s*$/, "$1");
    },
    /**
     * Convenience method for extracting the XSRF value used for POST, PUT or DELETE.
     * TODO: Multitype returns are bad design.
     * @return {String||undefined}
     */            
    xsrfExtract: function() {
        var name = "_xsrf";
        var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
        return r ? r[1] : undefined;
    },
    /**
     * Because innerHTML is sometimes not fast enough.
     * @param {Object} target DOM element target for innerHTML replacement.
     * @param {String} innerHTML The HTML to inject.
     * @return {Object} The target DOM element. WARNING! Could be a new cloned element.
     */            
    turboInnerHTML: function(target, innerHTML) {
        /*@cc_on //innerHTML is faster for IE
            target.innerHTML = innerHTML;
            return target;
        @*/
        var targetClone = target.cloneNode(false);
        targetClone.innerHTML = innerHTML;
        target.parentNode.replaceChild(targetClone, target);
        return targetClone;
    }
};
