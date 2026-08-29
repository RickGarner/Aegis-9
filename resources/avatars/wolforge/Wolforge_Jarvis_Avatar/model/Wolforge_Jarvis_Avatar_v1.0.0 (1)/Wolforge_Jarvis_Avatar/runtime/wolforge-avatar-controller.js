/* Offline WebView2/model-viewer controller for Wolforge Jarvis Avatar. */
(() => {
  const viewer = () => document.querySelector('model-viewer#wolforge-avatar');
  const looping = new Set(['Idle', 'Speaking', 'Thinking']);
  let current = 'Idle';

  function play(name, loop = looping.has(name)) {
    const v = viewer();
    if (!v) return false;
    current = name;
    v.pause();
    v.animationName = name;
    v.currentTime = 0;
    v.play({ repetitions: loop ? Infinity : 1 });
    if (!loop) {
      const done = () => { v.removeEventListener('finished', done); play('Idle', true); };
      v.addEventListener('finished', done);
    }
    return true;
  }

  window.WolforgeAvatar = {
    ready: () => !!viewer(),
    state: () => current,
    idle: () => play('Idle', true),
    blink: () => play('Blink', false),
    listen: () => play('Listening', false),
    think: () => play('Thinking', true),
    speak: () => play('Speaking', true),
    stopSpeaking: () => play('Idle', true),
    success: () => play('Success', false),
    warning: () => play('Warning', false),
    error: () => play('Error', false),
    jawTest: () => play('JawOpen', false),
    play
  };
})();
