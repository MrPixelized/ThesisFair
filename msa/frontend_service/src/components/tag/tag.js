import React from 'react'

import './tag.scss'

// Props has
// props.label
// props.selectable
// props.selected
// props.onClick
function Tag(props) {
  return (
    <div className='tag' onClick={props.onClick}>
      <span>{props.label}</span>
    </div>
  )
}

export default Tag
