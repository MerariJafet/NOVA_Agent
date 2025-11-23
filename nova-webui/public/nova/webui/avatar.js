// Avatar 3D con Three.js
// Avatar 3D: provide initAvatar() to be called after window.onload
(function(){
  function initAvatar(){
    const canvas = document.querySelector('#ai-avatar-container canvas');
    if(!canvas) return null;

    // Setup Three.js
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, canvas.clientWidth / canvas.clientHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio || 1);
    renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    camera.position.z = 5;

    // Head
    const headGeometry = new THREE.SphereGeometry(1.5, 32, 32);
    const headMaterial = new THREE.MeshPhongMaterial({ color:0x00d9ff, emissive:0x00d9ff, emissiveIntensity:0.3, shininess:100, transparent:true, opacity:0.95 });
    const head = new THREE.Mesh(headGeometry, headMaterial); scene.add(head);

    // Eyes
    const eyeGeometry = new THREE.SphereGeometry(0.15, 16, 16);
    const eyeMaterial = new THREE.MeshBasicMaterial({ color:0x00ffff });
    const leftEye = new THREE.Mesh(eyeGeometry, eyeMaterial); leftEye.position.set(-0.4,0.3,1.3); head.add(leftEye);
    const rightEye = new THREE.Mesh(eyeGeometry, eyeMaterial); rightEye.position.set(0.4,0.3,1.3); head.add(rightEye);

    // Lights
    scene.add(new THREE.AmbientLight(0x404040,2));
    const p1 = new THREE.PointLight(0x00d9ff,2,100); p1.position.set(5,5,5); scene.add(p1);
    const p2 = new THREE.PointLight(0xff6b35,1.5,100); p2.position.set(-5,-5,5); scene.add(p2);

    // Particles
    const particlesGeometry = new THREE.BufferGeometry();
    const particlesCount = 300; const posArray = new Float32Array(particlesCount*3);
    for(let i=0;i<particlesCount*3;i++) posArray[i]=(Math.random()-0.5)*12;
    particlesGeometry.setAttribute('position', new THREE.BufferAttribute(posArray,3));
    const particles = new THREE.Points(particlesGeometry, new THREE.PointsMaterial({ size:0.04, color:0x00d9ff, transparent:true, opacity:0.6 }));
    scene.add(particles);

    // Animate
    let t=0; function animate(){ requestAnimationFrame(animate); t+=0.01; head.rotation.y = Math.sin(t*0.5)*0.3; head.rotation.x = Math.sin(t*0.3)*0.08; if(Math.random()<0.01){ leftEye.scale.y=0.1; rightEye.scale.y=0.1; setTimeout(()=>{leftEye.scale.y=1; rightEye.scale.y=1;},120);} particles.rotation.y+=0.0008; renderer.render(scene,camera); }

    animate();

    // Responsive
    window.addEventListener('resize', ()=>{ camera.aspect = canvas.clientWidth / canvas.clientHeight; camera.updateProjectionMatrix(); renderer.setSize(canvas.clientWidth, canvas.clientHeight); });

    return { scene, camera, renderer };
  }

  // expose
  window.initAvatar = initAvatar;
})();
