import React from 'react'

// Copia sin editar del mismo archivo utilizado por la app Flutter/iOS.
export function BrandLogo({ className = '' }) {
  return <img className={`company-logo ${className}`.trim()} src="/brand/kill-bichos.png" alt="Kill Bichos, control de plagas" width="104" height="104" />
}
