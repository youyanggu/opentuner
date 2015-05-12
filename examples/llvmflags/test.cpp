#include <iostream>
#include <cmath>
#include <cstdlib>

int main() {
	int i, j, k;
	std::cout << abs((N*(500-N))) << '\n';
	for (i=0; i<abs((N*(500-N))); i++) {
		j = i;
		k = 0.2*j-i/2;
		j = k+1;
		k = j*0.32-1;
		j = k/2;
		k = j*0.12+1;
	}
	std::cout << k << '\n';
	return 0;
}
