import { Link, type LinkProps } from 'react-router-dom'
import buttonStyles from './Button.module.css'

interface LinkButtonProps extends LinkProps {
  variant?: 'primary' | 'secondary' | 'ghost'
}

/** Same visual as Button, but renders a router <Link> (an <a>) — for
 * navigation actions that must stay real links, not <button> elements. */
export function LinkButton({ variant = 'secondary', className, ...props }: LinkButtonProps) {
  return <Link className={`${buttonStyles.button} ${buttonStyles[variant]} ${className ?? ''}`} {...props} />
}
