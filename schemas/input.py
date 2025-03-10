INPUT_SCHEMA = {
    'workflow': {
        'type': str,
        'required': False,
        'default': 'txt2img',
        'constraints': lambda workflow: workflow in [
            'default',
            'txt2img',
            'custom'
        ]
    },
    'payload': {
        'type': dict,
        'required': True
    },
    'save_path': {
        'type': str,
        'required': False,
        'default': None
    },
    'overlay': {
        'type': dict,
        'required': False,
        'default': None,
        'schema': {
            'frame_img' :{
                'type': str,
                'required': False,
                'default': None
            },
            'logo_img': {
                'type': str,
                'required': False,
                'default': None
            },
            'logo_position': {
                'type': str,
                'required': False,
                'default': 'bottom-right',
                'constraints': lambda position: position in [
                    'top-left',
                    'top-right',
                    'bottom-left',
                    'bottom-right'
                ]
            },
        }
    }
}
