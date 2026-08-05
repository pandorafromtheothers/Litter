let lastKnownScrollPosition = 0;
let scrollAnchor = 0;
let triggerPoint = 200;
let shown = true;
let currentState = undefined;
let states = { down: 0, up: 1 };

function ShowElement(key, className) {
    let _element = document.querySelector(key);
    _element.classList.remove(className);
}
function HideElement(key, className){
    let _element = document.querySelector(key);
    _element.classList.add(className);
}

document.addEventListener("scroll", () => {
    if(window.innerWidth >= 600)
        return;
    let _lastState = currentState;

    currentState = lastKnownScrollPosition < window.scrollY ?  states.up : states.down;
    lastKnownScrollPosition = window.scrollY;

    if (_lastState != currentState)
        scrollAnchor = lastKnownScrollPosition;

    //console.log({ anchor: scrollAnchor, lastknown: lastKnownScrollPosition, state: currentState });
    
    if (scrollAnchor - lastKnownScrollPosition >= triggerPoint) {
        if (shown)
            return;

        ShowElement(".header", "header-hide");
        ShowElement(".mock-sidemenu", "bottom-nav-hide");
        shown = true;
    }
    if (lastKnownScrollPosition - scrollAnchor >= triggerPoint) {
        if (!shown)
            return;

        HideElement(".header", "header-hide");
        HideElement(".mock-sidemenu", "bottom-nav-hide");
        shown = false;
    }
});

