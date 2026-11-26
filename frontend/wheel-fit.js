const wheelFit = (() => {
  const diameters = Array.from({length: 9}, (_, index) => String(14 + index));
  const boreThresholds = [
    54.1, 56.6, 56.7, 57.1, 58.5, 58.6, 60.1, 63.3, 63.4, 65.1, 66.1,
    66.6, 67.1, 71.5, 71.6, 72.6, 73, 73.1, 74.1, 75.1, 77.8, 78.1, 84.1,
    89.1, 92.5, 95.1, 98.5, 100.1, 106.1, 106.2, 110, 110.1, 110.5
  ].map(String);
  const boltPatterns = [
    '4×98', '4×100', '4×114.3',
    '5×100', '5×108', '5×112', '5×114.3', '5×120', '5×130', '5×139.7', '6×139.7'
  ];
  let refresh = () => {};

  function diagram(host, markup) {
    host.innerHTML = `<svg viewBox="0 0 160 160" width="160" height="160" aria-hidden="true">${markup}</svg>`;
  }

  function attach(host) {
    const diameter = host.querySelector('[name=diameter]');
    const bolt = host.querySelector('[name=bolt_pattern]');
    for (const [select, values] of [
      [diameter, diameters],
      [bolt, boltPatterns]
    ]) {
      select.replaceChildren(new Option('Любой',''), ...values.map(value => new Option(value.replaceAll('.',','),value)));
    }
    for (const select of [diameter, bolt]) {
      const visual = document.createElement('span');
      visual.className = 'fit-diagram';
            const field = select.parentElement;
      const label = field.querySelector('label');
      const trigger = document.createElement('button');
      trigger.type = 'button';
      trigger.className = 'fit-trigger';
      trigger.id = select.id + '-diagram';
      label.htmlFor = trigger.id;
      label.hidden = true;
      trigger.setAttribute('aria-expanded', 'false');
      trigger.append(visual);
      const menu = document.createElement('div');
      const dial = select === diameter;
      menu.className = dial ? 'fit-menu fit-dial' : 'fit-menu fit-list';
      menu.hidden = true;
      select.hidden = true;
      field.append(trigger, menu);

      function close() {
        menu.hidden = true;
        trigger.setAttribute('aria-expanded', 'false');
        refresh();
      }
      for (const [index, option] of [...select.options].entries()) {
        if (dial && !option.value) continue;
        const choice = document.createElement('button');
        choice.type = 'button';
        choice.textContent = option.text;
        choice.dataset.value = option.value;
        if (dial) {
          const angle = (index - 1) * 2 * Math.PI / (select.options.length - 1) - Math.PI / 2;
          choice.style.left = index ? (50 + 36 * Math.cos(angle)) + '%' : '50%';
          choice.style.top = index ? (50 + 36 * Math.sin(angle)) + '%' : '50%';
        }
        choice.onclick = () => {
          select.value = option.value;
          select.dispatchEvent(new Event('input', { bubbles: true }));
          select.dispatchEvent(new Event('change', { bubbles: true }));
          close();
          trigger.focus();
        };
        menu.append(choice);
      }
      trigger.onclick = () => {
        if (!menu.hidden) { close(); return; }
        menu.hidden = false;
        (menu.querySelector('[aria-pressed="true"]') || menu.firstElementChild).focus();
        trigger.setAttribute('aria-expanded', 'true');
      };
      field.addEventListener('focusout', event => {
        if (!field.contains(event.relatedTarget) && !menu.hidden) { close(); }
      });
      field.addEventListener('keydown', event => {
        if (event.key === 'Escape' && !menu.hidden) {
          close();
          trigger.focus();
        }
      });


    }
    const left = diameter.parentElement.querySelector(".fit-diagram");
    const right = bolt.parentElement.querySelector(".fit-diagram");
    refresh = () => {
      if (!host.contains(diameter)) return;
      for (const select of [diameter, bolt]) {
        const field = select.parentElement;
        field.querySelector('.fit-trigger').setAttribute('aria-label',
          field.querySelector('label').textContent + ': ' + select.selectedOptions[0].text);
        for (const choice of field.querySelectorAll('.fit-menu button')) {
          choice.setAttribute('aria-pressed', String(choice.dataset.value === select.value));
        }
      }
      const d = Number(diameter.value) || 16;
      const centerY = 70;
      const radius = 65;
      diagram(left, `<circle class="fit-rim" cx="80" cy="${centerY}" r="${radius}"/>

        <text class="${diameter.value ? 'fit-size-value' : 'fit-placeholder'}" x="80" y="${centerY}" dominant-baseline="central" text-anchor="middle">${diameter.value ? d+'″' : 'Диаметр'}</text>`);
      const [holes, mm] = bolt.value ? bolt.value.split('×').map(Number) : [0,114.3];
      const pitch = Math.min(40, Math.max(30, 32 + (mm - 98) * .26));
      const dots = Array.from({length:holes},(_,i) => {
        const angle = i*2*Math.PI/holes-Math.PI/2;
        return `<circle class="fit-hole" cx="${80+pitch*Math.cos(angle)}" cy="${centerY+pitch*Math.sin(angle)}" r="5"/>`;
      }).join('');
      diagram(right, `<circle class="fit-rim" cx="80" cy="${centerY}" r="${radius}"/>
        ${dots}
        <text class="${holes ? '' : 'fit-placeholder'}" x="80" y="${holes ? 153 : centerY + 5}" text-anchor="middle">${holes ? bolt.value.replace('.', ',') : 'Разболтовка'}</text>`);
    };
    diameter.addEventListener('change',refresh);
    bolt.addEventListener('change',refresh);
    refresh();
  }
  return {attach, centerBores: () => boreThresholds, refresh: () => refresh()};
})();













