import type { ButtonHTMLAttributes } from 'react'
import styles from './Button.module.css'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost'
}

export function Button({ variant = 'secondary', className, ...props }: ButtonProps) {
  return <button className={`${styles.button} ${styles[variant]} ${className ?? ''}`} {...props} />
}
