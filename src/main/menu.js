/**
 * Application menu. Shortcuts are handled in the renderer (so they don't
 * steal keys from text fields); the menu only displays them.
 */

const { Menu } = require('electron');

const FPS_OPTIONS = [10, 20, 30, 60];

function buildMenu({ send, connected, targetFps, onToggleConnection, onQuit }) {
  const item = (label, command, accelerator) => ({
    label,
    accelerator,
    registerAccelerator: false,
    click: () => send(command),
  });

  const template = [
    {
      label: 'File',
      submenu: [
        item('New Theme', 'new-theme', 'CmdOrCtrl+N'),
        item('Open Theme...', 'open-theme', 'CmdOrCtrl+O'),
        item('Save', 'quick-save', 'CmdOrCtrl+S'),
        item('Save As...', 'save-theme-as', 'CmdOrCtrl+Shift+S'),
        { type: 'separator' },
        item('Export as Image...', 'export-image'),
        item('Open Presets Folder', 'open-presets-folder'),
        { type: 'separator' },
        { label: 'Exit', click: onQuit },
      ],
    },
    {
      label: 'Edit',
      submenu: [
        item('Undo', 'undo', 'CmdOrCtrl+Z'),
        item('Redo', 'redo', 'CmdOrCtrl+Y'),
        { type: 'separator' },
        item('Duplicate', 'duplicate', 'CmdOrCtrl+D'),
        item('Delete', 'delete', 'Delete'),
        { type: 'separator' },
        item('Group', 'group', 'CmdOrCtrl+G'),
        item('Ungroup', 'ungroup', 'CmdOrCtrl+Shift+G'),
      ],
    },
    {
      label: 'Display',
      submenu: [
        { label: connected ? 'Disconnect' : 'Connect', click: onToggleConnection },
        { type: 'separator' },
        {
          label: 'Frame Rate',
          submenu: FPS_OPTIONS.map((fps) => ({
            label: `${fps} FPS`,
            type: 'radio',
            checked: fps === targetFps,
            click: () => send('set-fps', fps),
          })),
        },
        { type: 'separator' },
        item('Diagnose Sensors...', 'diagnose-sensors'),
      ],
    },
    {
      label: 'Settings',
      submenu: [
        item('Preferences...', 'preferences'),
        { type: 'separator' },
        { label: 'Developer Tools', role: 'toggleDevTools' },
      ],
    },
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

module.exports = { buildMenu };
