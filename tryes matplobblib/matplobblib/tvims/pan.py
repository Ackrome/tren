from rrstr import *
#######################################################################################################################
# Портфельный анализ с невырожденной ковариационной матрицей
#######################################################################################################################
def PAN_3(e_a,e_b,s_a,s_b, r_ab):
    """Математическое ожидание доходности акций компаний А и В составляет `e_a`% и `e_b`%, 
    при этом стандартное отклонение доходности равно `s_a`% и `s_b`%, соответственно. Также известен 
    коэффициент корреляции доходностей акций А и В, `r_ab`. Найдите (короткие позиции допускаются):
    - доли акций А и В в портфеле с минимальной дисперсией доходности;
    - ожидаемую доходность и стандартное отклонение доходности такого портфеля.

    Args:
        e_a (numerical): Математическое ожидание доходности акции компаний А
        e_b (numerical): Математическое ожидание доходности акции компаний В
        s_a (numerical): Стандартное отклонение доходности акции компаний А
        s_b (numerical): Стандартное отклонение доходности акции компаний В 
        r_ab (numerical): Коэффициент корреляции доходностей акций А и В

    ## Prints
        `answer` каждое значение по очереди.<br>C запятой вместо точки и сокращением до соответствующего количества знаков после запятой

    Returns:
        `answer` (tuple): Соответствующие величины
    """


    muA, muB = e_a/100, e_b/100
    sigmaA, sigmaB = s_a/100, s_b/100

    roAB = r_ab

    a = (sigmaB**2 - roAB*sigmaA*sigmaB) / (sigmaA**2 + sigmaB**2 - 2*roAB*sigmaA*sigmaB)
    b = 1-a
    muR = a*muA + b*muB
    VarR = (a**2)*(sigmaA**2) + (b**2)*(sigmaB**2) + 2*a*b*roAB*sigmaA*sigmaB

    answer = (a,b,muR*100,(VarR**0.5)*100)
    
    print('Доля А = ' + rrstr(answer[0],2) + '; доля В = ' + rrstr(answer[1],2))
    print('Ожидаемая доходность = ' + rrstr(answer[2],1) + '; стандартное отклонение = ' + rrstr(answer[3],1))

    return answer
#######################################################################################################################
PAN = [PAN_3]