"""
Sistema de animaciones para la interfaz basado en QRect.
Animaciones de geometría (posición + tamaño) sin opacidad para evitar errores QPainter.
"""
from PyQt6.QtCore import (QPropertyAnimation, QEasingCurve, QPoint, QSize, 
                          QRect, QSequentialAnimationGroup)


class GeometryAnimator:
    """Clase para animaciones basadas en QRect (geometría completa)."""
    
    @staticmethod
    def expand_from_center(widget, target_rect: QRect, duration=300):
        """
        Expandir widget desde el centro hacia un tamaño objetivo.
        Útil para modales, popups y cards que aparecen.
        """
        center = target_rect.center()
        start_rect = QRect(center.x(), center.y(), 0, 0)
        
        anim = QPropertyAnimation(widget, b"geometry")
        anim.setDuration(duration)
        anim.setStartValue(start_rect)
        anim.setEndValue(target_rect)
        anim.setEasingCurve(QEasingCurve.Type.OutBack)
        return anim
    
    @staticmethod
    def collapse_to_center(widget, duration=250, on_finished=None):
        """
        Colapsar widget hacia su centro.
        Útil para cerrar modales/popups.
        """
        current_rect = widget.geometry()
        center = current_rect.center()
        end_rect = QRect(center.x(), center.y(), 0, 0)
        
        anim = QPropertyAnimation(widget, b"geometry")
        anim.setDuration(duration)
        anim.setStartValue(current_rect)
        anim.setEndValue(end_rect)
        anim.setEasingCurve(QEasingCurve.Type.InBack)
        
        if on_finished:
            anim.finished.connect(on_finished)
        return anim
    
    @staticmethod
    def morph_to(widget, target_rect: QRect, duration=350):
        """
        Transformar suavemente la geometría del widget.
        Útil para redimensionar paneles, cambiar layouts.
        """
        anim = QPropertyAnimation(widget, b"geometry")
        anim.setDuration(duration)
        anim.setStartValue(widget.geometry())
        anim.setEndValue(target_rect)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        return anim
    
    @staticmethod
    def pulse(widget, scale_factor=1.1, duration=200):
        """
        Efecto de pulso: agranda y vuelve al tamaño original.
        Útil para feedback visual en botones o notificaciones.
        """
        original_rect = widget.geometry()
        center = original_rect.center()
        
        # Calcular rect expandido
        new_width = int(original_rect.width() * scale_factor)
        new_height = int(original_rect.height() * scale_factor)
        expanded_rect = QRect(
            center.x() - new_width // 2,
            center.y() - new_height // 2,
            new_width,
            new_height
        )
        
        # Animación secuencial: expandir y contraer
        group = QSequentialAnimationGroup(widget)
        
        expand = QPropertyAnimation(widget, b"geometry")
        expand.setDuration(duration // 2)
        expand.setStartValue(original_rect)
        expand.setEndValue(expanded_rect)
        expand.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        contract = QPropertyAnimation(widget, b"geometry")
        contract.setDuration(duration // 2)
        contract.setStartValue(expanded_rect)
        contract.setEndValue(original_rect)
        contract.setEasingCurve(QEasingCurve.Type.InQuad)
        
        group.addAnimation(expand)
        group.addAnimation(contract)
        return group
    
    @staticmethod
    def slide_and_resize(widget, target_rect: QRect, duration=400):
        """
        Deslizar y redimensionar simultáneamente.
        Útil para paneles laterales que se expanden/contraen.
        """
        anim = QPropertyAnimation(widget, b"geometry")
        anim.setDuration(duration)
        anim.setStartValue(widget.geometry())
        anim.setEndValue(target_rect)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        return anim
    
    @staticmethod
    def shake(widget, intensity=5, duration=300):
        """
        Efecto de sacudida horizontal.
        Útil para indicar error en formularios.
        """
        original_rect = widget.geometry()
        
        group = QSequentialAnimationGroup(widget)
        
        positions = [intensity, -intensity, intensity // 2, -intensity // 2, 0]
        step_duration = duration // len(positions)
        
        for offset in positions:
            anim = QPropertyAnimation(widget, b"geometry")
            anim.setDuration(step_duration)
            shake_rect = QRect(
                original_rect.x() + offset,
                original_rect.y(),
                original_rect.width(),
                original_rect.height()
            )
            anim.setEndValue(shake_rect)
            anim.setEasingCurve(QEasingCurve.Type.Linear)
            group.addAnimation(anim)
        
        return group


class AnimationMixin:
    """Mixin que provee métodos de animación QRect para widgets."""
    
    def expand_from_point(self, point: QPoint = None, duration=300):
        """Expandir widget desde un punto (útil para menús contextuales)."""
        if not hasattr(self, '_expand_anim'):
            self._expand_anim = None
        
        target_rect = self.geometry()
        if point is None:
            point = target_rect.center()
        
        start_rect = QRect(point.x(), point.y(), 0, 0)
        self.setGeometry(start_rect)
        self.show()
        
        self._expand_anim = QPropertyAnimation(self, b"geometry")
        self._expand_anim.setDuration(duration)
        self._expand_anim.setStartValue(start_rect)
        self._expand_anim.setEndValue(target_rect)
        self._expand_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self._expand_anim.start()
        
        return self._expand_anim
    
    def collapse_to_point(self, point: QPoint = None, duration=250, on_finished=None):
        """Colapsar widget hacia un punto."""
        if not hasattr(self, '_collapse_anim'):
            self._collapse_anim = None
        
        current_rect = self.geometry()
        if point is None:
            point = current_rect.center()
        
        end_rect = QRect(point.x(), point.y(), 0, 0)
        
        self._collapse_anim = QPropertyAnimation(self, b"geometry")
        self._collapse_anim.setDuration(duration)
        self._collapse_anim.setStartValue(current_rect)
        self._collapse_anim.setEndValue(end_rect)
        self._collapse_anim.setEasingCurve(QEasingCurve.Type.InBack)
        
        if on_finished:
            self._collapse_anim.finished.connect(on_finished)
        
        self._collapse_anim.start()
        return self._collapse_anim
    
    def resize_animated(self, new_size: QSize, duration=300):
        """Redimensionar widget con animación manteniendo posición."""
        if not hasattr(self, '_resize_anim'):
            self._resize_anim = None
        
        current_rect = self.geometry()
        target_rect = QRect(current_rect.topLeft(), new_size)
        
        self._resize_anim = QPropertyAnimation(self, b"geometry")
        self._resize_anim.setDuration(duration)
        self._resize_anim.setStartValue(current_rect)
        self._resize_anim.setEndValue(target_rect)
        self._resize_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._resize_anim.start()
        
        return self._resize_anim
    
    def move_and_resize(self, target_rect: QRect, duration=350):
        """Mover y redimensionar simultáneamente."""
        if not hasattr(self, '_morph_anim'):
            self._morph_anim = None
        
        self._morph_anim = QPropertyAnimation(self, b"geometry")
        self._morph_anim.setDuration(duration)
        self._morph_anim.setStartValue(self.geometry())
        self._morph_anim.setEndValue(target_rect)
        self._morph_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._morph_anim.start()
        
        return self._morph_anim
    
    def pulse_effect(self, scale=1.08, duration=200):
        """Efecto de pulso para feedback visual."""
        if not hasattr(self, '_pulse_group'):
            self._pulse_group = None
        
        self._pulse_group = GeometryAnimator.pulse(self, scale, duration)
        self._pulse_group.start()
        return self._pulse_group
    
    def shake_effect(self, intensity=6, duration=300):
        """Efecto de sacudida para indicar error."""
        if not hasattr(self, '_shake_group'):
            self._shake_group = None
        
        self._shake_group = GeometryAnimator.shake(self, intensity, duration)
        self._shake_group.start()
        return self._shake_group
